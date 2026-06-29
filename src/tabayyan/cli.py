"""Command-line interface for Tabayyan. Stdlib only.

Commands:
  tabayyan scan    [paths...]  detect entities, print findings
  tabayyan redact  [paths...]  detect + redact, print sanitised text

Reads stdin when no path is given or path is '-'. Supports batch over
files and directories. Exit code is non-zero when entities are found,
so it slots into CI / pre-commit gates.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from . import __version__
from .config import Config
from .engine import DetectionEngine
from .streaming import scan_file
from .entities import Confidence, Match
from .homoglyph import scan_text as _scan_domains
from .redaction import RedactionMode, redact

_CONFIDENCE_ORDER = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}
_TEXT_SUFFIXES = {".txt", ".md", ".log", ".json", ".csv", ".eml", ".text"}


def _iter_inputs(paths: list[str]) -> Iterable[tuple[str, str]]:
    """Yield (source_name, text). '-' or empty -> stdin."""
    if not paths or paths == ["-"]:
        yield ("<stdin>", sys.stdin.read())
        return
    for raw in paths:
        if raw == "-":
            yield ("<stdin>", sys.stdin.read())
            continue
        p = Path(raw)
        if p.is_dir():
            for child in sorted(p.rglob("*")):
                if child.is_file() and child.suffix.lower() in _TEXT_SUFFIXES:
                    yield (str(child), child.read_text(encoding="utf-8", errors="replace"))
        elif p.is_file():
            yield (str(p), p.read_text(encoding="utf-8", errors="replace"))
        else:
            print(f"tabayyan: cannot read '{raw}'", file=sys.stderr)


def _engine_from_args(args) -> DetectionEngine:
    cfg = getattr(args, "config", None)
    return Config.from_file(cfg).build_engine() if cfg else DetectionEngine()


def _filter_matches(matches: list[Match], args) -> list[Match]:
    out = matches
    if args.min_confidence:
        floor = _CONFIDENCE_ORDER[Confidence(args.min_confidence)]
        out = [m for m in out if _CONFIDENCE_ORDER[m.confidence] >= floor]
    if args.only:
        only = set(args.only)
        out = [m for m in out if m.entity_type.value in only]
    if args.exclude:
        excl = set(args.exclude)
        out = [m for m in out if m.entity_type.value not in excl]
    return out


def _cmd_scan(args) -> int:
    engine = _engine_from_args(args)
    found_any = False
    report = []
    if args.stream:
        for raw in args.paths:
            if raw in ("", "-"):
                print("tabayyan: --stream requires file paths, not stdin", file=sys.stderr)
                continue
            matches = _filter_matches(list(scan_file(raw, engine)), args)
            if matches:
                found_any = True
            if args.json:
                report.append({"source": raw, "matches": [m.to_dict() for m in matches]})
            else:
                for m in matches:
                    val = "" if args.no_values else f"  {m.value!r}"
                    print(f"{raw}:{m.start}-{m.end}\t{m.entity_type.value}\t"
                          f"{m.confidence.value}\t{m.category.value}{val}")
        if args.json:
            json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
        return (1 if found_any else 0) if args.fail_on_find else 0
    for name, text in _iter_inputs(args.paths):
        matches = _filter_matches(engine.scan(text), args)
        if matches:
            found_any = True
        if args.json:
            report.append({"source": name, "matches": [m.to_dict() for m in matches]})
        else:
            for m in matches:
                val = "" if args.no_values else f"  {m.value!r}"
                print(f"{name}:{m.start}-{m.end}\t{m.entity_type.value}\t"
                      f"{m.confidence.value}\t{m.category.value}{val}")
    if args.json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    return (1 if found_any else 0) if args.fail_on_find else 0


def _cmd_redact(args) -> int:
    engine = _engine_from_args(args)
    mode = RedactionMode(args.mode)
    if mode is RedactionMode.HASH and not args.salt:
        print(
            "error: --mode hash requires a non-empty --salt (used as the HMAC key); "
            "an empty key leaves short identifiers reversible by brute force.",
            file=sys.stderr,
        )
        return 2
    found_any = False
    inputs = list(_iter_inputs(args.paths))
    multi = len(inputs) > 1
    for name, text in inputs:
        matches = _filter_matches(engine.scan(text), args)
        if matches:
            found_any = True
        result = redact(
            text, matches, mode,
            salt=args.salt, hash_length=args.hash_length,
            partial_keep_last=args.keep_last,
        )
        if args.json:
            payload = result.to_dict()
            payload["source"] = name
            json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
        else:
            if multi:
                print(f"===== {name} =====")
            sys.stdout.write(result.text)
            if not result.text.endswith("\n"):
                sys.stdout.write("\n")
            if result.vault:
                print(f"# vault ({len(result.vault)} tokens) — store securely; "
                      f"use --json to capture", file=sys.stderr)
    return (1 if found_any else 0) if args.fail_on_find else 0


def _load_watchlist(path: str | None) -> list[str]:
    if not path:
        return []
    return [ln.strip() for ln in Path(path).read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")]


def _cmd_domains(args) -> int:
    watchlist = _load_watchlist(args.watchlist)
    found_any = False
    report = []
    for name, text in _iter_inputs(args.paths):
        findings = _scan_domains(text, watchlist,
                                 typosquat_max_distance=args.max_distance)
        if findings:
            found_any = True
        if args.json:
            report.append({"source": name, "findings": [vars(f) for f in findings]})
        else:
            for f in findings:
                tgt = f" -> {f.target}" if f.target else ""
                print(f"{name}:{f.start}-{f.end}\t{f.domain}\t{f.reason}\t"
                      f"{f.confidence}{tgt}\t{f.detail}")
    if args.json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    return (1 if found_any else 0) if args.fail_on_find else 0


def _add_common_filters(p: argparse.ArgumentParser) -> None:
    p.add_argument("paths", nargs="*", help="files/dirs, or '-' for stdin")
    p.add_argument("--min-confidence", choices=["low", "medium", "high"],
                   help="drop matches below this confidence")
    p.add_argument("--only", nargs="+", metavar="TYPE", help="keep only these entity types")
    p.add_argument("--exclude", nargs="+", metavar="TYPE", help="drop these entity types")
    p.add_argument("--json", action="store_true", help="emit JSON")
    p.add_argument("--fail-on-find", action="store_true",
                   help="exit 1 if any entity is found (for CI / pre-commit)")
    p.add_argument("--config", help="JSON config: disable/add detectors, thresholds")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tabayyan", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"tabayyan {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    ps = sub.add_parser("scan", help="detect entities")
    _add_common_filters(ps)
    ps.add_argument("--no-values", action="store_true", help="hide raw values in output")
    ps.add_argument("--stream", action="store_true",
                    help="scan large files incrementally (file paths only)")
    ps.set_defaults(func=_cmd_scan)

    pr = sub.add_parser("redact", help="detect and redact")
    _add_common_filters(pr)
    pr.add_argument("--mode", choices=[m.value for m in RedactionMode], default="mask")
    pr.add_argument("--salt", default="", help="HMAC key for hash mode (required, non-empty)")
    pr.add_argument("--hash-length", type=int, default=12, help="hash token length")
    pr.add_argument("--keep-last", type=int, default=4, help="kept chars in partial mode")
    pr.set_defaults(func=_cmd_redact)
    pd = sub.add_parser("domains", help="detect lookalike / homoglyph domains")
    pd.add_argument("paths", nargs="*", help="files/dirs, or '-' for stdin")
    pd.add_argument("--watchlist", help="file of legitimate domains, one per line")
    pd.add_argument("--max-distance", type=int, default=1,
                    help="max edit distance for typosquat flag")
    pd.add_argument("--json", action="store_true", help="emit JSON")
    pd.add_argument("--fail-on-find", action="store_true",
                    help="exit 1 if any suspicious domain is found")
    pd.set_defaults(func=_cmd_domains)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
