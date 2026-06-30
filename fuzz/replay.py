"""Replay saved fuzz inputs through the same invariants — no Atheris needed.

    python -m fuzz.replay fuzz/artifacts/crash-abc123
    python -m fuzz.replay fuzz/seeds/*

Exits non-zero on the first input that violates an invariant, printing which
one — turning a fuzzer crash into a one-command, dependency-free repro.
"""
from __future__ import annotations

import sys
from pathlib import Path

from fuzz.harness import run_bytes


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python -m fuzz.replay <input-file> [more ...]")
        return 2
    failed = False
    for arg in argv:
        data = Path(arg).read_bytes()
        try:
            run_bytes(data)
            print(f"OK    {arg}")
        except AssertionError as exc:
            print(f"FAIL  {arg}: {exc}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
