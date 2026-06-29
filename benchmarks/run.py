"""Reproducible benchmark for the Tabayyan detection engine.

Builds a labelled SYNTHETIC corpus of positives (text containing a known
entity) and hard negatives (look-alikes that must NOT match), runs the
engine, and reports precision / recall / F1 per entity type. It also
contrasts against a naive format-only regex baseline to quantify the
false positives that checksum validation removes.

Honesty note: this measures detectors against a synthetic distribution we
designed. It is a regression and sanity signal, not a claim about
real-world traffic. The value is in the hard negatives and the naive
baseline comparison.

Run:  python benchmarks/run.py            # prints tables
      python benchmarks/run.py --write    # also writes benchmarks/RESULTS.md
"""
from __future__ import annotations

import argparse
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from tabayyan import DetectionEngine, EntityType
from tests.synthetic import (
    make_credit_card, make_iban, make_invalid_iban, make_invalid_national_id,
    make_landline, make_mobile, make_national_address, make_national_id,
    make_passport, make_unified_number, make_vat,
)

N = 300  # samples per generator


@dataclass
class Sample:
    text: str
    gold_type: EntityType | None  # None == hard negative
    focus: EntityType


def _wrap(rng: random.Random, value: str) -> str:
    templates = ["patient record {v} filed", "ref: {v}.", "see {v} attached",
                 "value={v}", "  {v}  "]
    return rng.choice(templates).format(v=value)


# Context phrases the context-gated detectors require nearby. Positives wrap a
# valid value WITH context; the matching hard negative wraps a valid-format
# value WITHOUT context — which must NOT be flagged (precision of the gate).
_CONTEXT_TEMPLATES = {
    EntityType.SAUDI_VAT: ["VAT no {v}", "الرقم الضريبي {v}", "tax registration {v}"],
    EntityType.SAUDI_PASSPORT: ["passport {v}", "رقم الجواز {v}"],
    EntityType.SAUDI_BORDER_NUMBER: ["border number {v}", "رقم الحدود {v}"],
    EntityType.SAUDI_NATIONAL_ADDRESS: ["national address {v}", "العنوان الوطني {v}"],
    EntityType.SAUDI_UNIFIED_NUMBER: ["unified number {v}", "الرقم الموحد {v}"],
}


def _ctx_wrap(rng: random.Random, kind: EntityType, value: str) -> str:
    return rng.choice(_CONTEXT_TEMPLATES[kind]).format(v=value)


def _make_border(rng: random.Random) -> str:
    # 10 digits starting 3-9 so it is not a (1/2-leading) National ID / Iqama.
    return str(rng.randint(3, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(9))


def add_new_entities(rng: random.Random, s: list) -> None:
    """Positives (with context where required) + hard negatives for the
    entities added after the original benchmark."""
    for _ in range(N):
        # Landline is reliable standalone; hard negative = invalid area code (1[89]).
        s.append(Sample(_wrap(rng, make_landline(rng)), EntityType.SAUDI_LANDLINE, EntityType.SAUDI_LANDLINE))
        bad_area = "01" + str(rng.choice((8, 9))) + "".join(str(rng.randint(0, 9)) for _ in range(7))
        s.append(Sample(_wrap(rng, bad_area), None, EntityType.SAUDI_LANDLINE))

        # Context-gated: positive WITH context, hard negative WITHOUT context.
        ctx_cases = [
            (EntityType.SAUDI_VAT, make_vat(rng)),
            (EntityType.SAUDI_PASSPORT, make_passport(rng)),
            (EntityType.SAUDI_BORDER_NUMBER, _make_border(rng)),
            (EntityType.SAUDI_NATIONAL_ADDRESS, make_national_address(rng)),
            (EntityType.SAUDI_UNIFIED_NUMBER, make_unified_number(rng)),
        ]
        for kind, value in ctx_cases:
            s.append(Sample(_ctx_wrap(rng, kind, value), kind, kind))
            s.append(Sample(_wrap(rng, value), None, kind))  # valid format, no context


def build_corpus(rng: random.Random) -> list[Sample]:
    s: list[Sample] = []
    for _ in range(N):
        s.append(Sample(_wrap(rng, make_national_id(rng, "1")), EntityType.SAUDI_NATIONAL_ID, EntityType.SAUDI_NATIONAL_ID))
        s.append(Sample(_wrap(rng, make_national_id(rng, "2")), EntityType.SAUDI_IQAMA, EntityType.SAUDI_IQAMA))
        s.append(Sample(_wrap(rng, make_iban(rng)), EntityType.SAUDI_IBAN, EntityType.SAUDI_IBAN))
        s.append(Sample(_wrap(rng, make_credit_card(rng, 16)), EntityType.CREDIT_CARD, EntityType.CREDIT_CARD))
        s.append(Sample(_wrap(rng, make_mobile(rng, rng.choice(["+966", "966", "0"]))), EntityType.SAUDI_MOBILE, EntityType.SAUDI_MOBILE))

        # hard negatives
        s.append(Sample(_wrap(rng, make_invalid_national_id(rng, "1")), None, EntityType.SAUDI_NATIONAL_ID))
        s.append(Sample(_wrap(rng, make_invalid_national_id(rng, "2")), None, EntityType.SAUDI_IQAMA))
        s.append(Sample(_wrap(rng, make_invalid_iban(rng)), None, EntityType.SAUDI_IBAN))
        valid_pan = make_credit_card(rng, 16)
        s.append(Sample(_wrap(rng, valid_pan[:-1] + str((int(valid_pan[-1]) + 1) % 10)), None, EntityType.CREDIT_CARD))

    add_new_entities(rng, s)
    rng.shuffle(s)
    return s


# --- evasion-robustness benchmark -------------------------------------------
# Recall on positives obfuscated with characters that look normal but break a
# naive regex. The normalization pre-pass should keep detection intact.
_AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
_FW_DIGITS = str.maketrans("0123456789", "０１２３４５６７８９")
_ZWSP = "​"


def _evasions(value: str):
    mid = len(value) // 2
    return {
        "zero_width": value[:mid] + _ZWSP + value[mid:],
        "arabic_indic": value.translate(_AR_DIGITS),
        "fullwidth": value.translate(_FW_DIGITS),
    }


def evaluate_evasion(rng: random.Random) -> dict[str, dict[str, int]]:
    """For each obfuscation, recall over checksum-valid IDs/IBANs, comparing
    the normalizing engine against one with normalization disabled."""
    norm_engine = DetectionEngine()
    raw_engine = DetectionEngine(normalize_input=False)
    techniques = ["zero_width", "arabic_indic", "fullwidth"]
    out = {t: {"norm_hit": 0, "raw_hit": 0, "total": 0} for t in techniques}
    for _ in range(N):
        cases = [
            (make_national_id(rng, "1"), EntityType.SAUDI_NATIONAL_ID),
            (make_iban(rng), EntityType.SAUDI_IBAN),
        ]
        for value, kind in cases:
            for tech, obf in _evasions(value).items():
                text = f"id {obf}"
                out[tech]["total"] += 1
                if kind in {m.entity_type for m in norm_engine.scan(text)}:
                    out[tech]["norm_hit"] += 1
                if kind in {m.entity_type for m in raw_engine.scan(text)}:
                    out[tech]["raw_hit"] += 1
    return out


def render_evasion(stats) -> str:
    lines = ["## Evasion robustness — recall on obfuscated identifiers", "",
             "Checksum-valid National IDs and IBANs hidden behind look-alike",
             "characters. The normalization pre-pass restores detection; without",
             "it, recall collapses. Higher is better.", "",
             "| Technique | Recall (normalized) | Recall (no normalization) |",
             "|---|---:|---:|"]
    for tech in ("zero_width", "arabic_indic", "fullwidth"):
        d = stats[tech]
        n = d["total"] or 1
        lines.append(f"| {tech} | {d['norm_hit'] / n:.3f} | {d['raw_hit'] / n:.3f} |")
    return "\n".join(lines)


def evaluate(samples: list[Sample]) -> dict[EntityType, dict[str, int]]:
    engine = DetectionEngine()
    stats: dict[EntityType, dict[str, int]] = {}

    def bump(t, key):
        stats.setdefault(t, {"tp": 0, "fp": 0, "fn": 0})[key] += 1

    for sample in samples:
        detected = {m.entity_type for m in engine.scan(sample.text)}
        if sample.gold_type is not None:
            bump(sample.gold_type, "tp" if sample.gold_type in detected else "fn")
        elif sample.focus in detected:
            bump(sample.focus, "fp")
    return stats


# Naive baseline: same formats, NO checksum validation.
_NAIVE = {
    EntityType.SAUDI_NATIONAL_ID: re.compile(r"(?<!\d)1\d{9}(?!\d)"),
    EntityType.SAUDI_IQAMA: re.compile(r"(?<!\d)2\d{9}(?!\d)"),
    EntityType.SAUDI_IBAN: re.compile(r"(?<![A-Z0-9])SA\d{2}(?:\s?[A-Z0-9]){20}(?![A-Z0-9])", re.I),
    EntityType.CREDIT_CARD: re.compile(r"(?<!\d)(?:\d[ \-]?){12,18}\d(?!\d)"),
}


def evaluate_naive(samples: list[Sample]) -> dict[EntityType, dict[str, int]]:
    stats: dict[EntityType, dict[str, int]] = {}

    def bump(t, key):
        stats.setdefault(t, {"tp": 0, "fp": 0, "fn": 0})[key] += 1

    for sample in samples:
        rx = _NAIVE.get(sample.focus)
        if rx is None:
            continue
        hit = bool(rx.search(sample.text))
        if sample.gold_type is not None:
            bump(sample.gold_type, "tp" if hit else "fn")
        elif hit:
            bump(sample.focus, "fp")
    return stats


def _prf(d):
    tp, fp, fn = d["tp"], d["fp"], d["fn"]
    p = tp / (tp + fp) if (tp + fp) else 1.0
    r = tp / (tp + fn) if (tp + fn) else 1.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def render(stats) -> str:
    lines = ["| Entity type | TP | FP | FN | Precision | Recall | F1 |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    macro = []
    for t in sorted(stats, key=lambda x: x.value):
        d = stats[t]
        p, r, f = _prf(d)
        macro.append((p, r, f))
        lines.append(f"| {t.value} | {d['tp']} | {d['fp']} | {d['fn']} | {p:.3f} | {r:.3f} | {f:.3f} |")
    if macro:
        mp = sum(x[0] for x in macro) / len(macro)
        mr = sum(x[1] for x in macro) / len(macro)
        mf = sum(x[2] for x in macro) / len(macro)
        lines.append(f"| **macro avg** |  |  |  | **{mp:.3f}** | **{mr:.3f}** | **{mf:.3f}** |")
    return "\n".join(lines)


def render_comparison(tab, naive) -> str:
    lines = ["## False positives on hard negatives — naive regex vs Tabayyan", "",
             "Each row counts how many look-alike decoys (invalid checksum, wrong",
             "leading digit) each approach wrongly flagged. Lower is better.", "",
             "| Entity type | Naive regex FP | Tabayyan FP | FP eliminated |",
             "|---|---:|---:|---:|"]
    for t in sorted(naive, key=lambda x: x.value):
        nfp = naive[t]["fp"]
        tfp = tab.get(t, {}).get("fp", 0)
        lines.append(f"| {t.value} | {nfp} | {tfp} | {nfp - tfp} |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--seed", type=int, default=1234)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    corpus = build_corpus(rng)
    stats = evaluate(corpus)
    naive = evaluate_naive(corpus)
    evasion = evaluate_evasion(random.Random(args.seed + 1))
    table = render(stats)
    comparison = render_comparison(stats, naive)
    evasion_table = render_evasion(evasion)

    header = (
        f"# Benchmark results\n\nSynthetic corpus, seed={args.seed}, "
        f"{len(corpus)} samples (positives + hard negatives).\n\n"
        "> Note: `saudi_vat` recall is below 1.0 because a 15-digit VAT that is "
        "coincidentally Luhn-valid is claimed by the higher-confidence "
        "`credit_card` detector. The span is still redacted — only the entity "
        "*type* differs — so this is a labelling overlap, not a missed PII.\n\n"
    )
    out = header + table + "\n\n" + comparison + "\n\n" + evasion_table
    print(out)
    if args.write:
        Path(__file__).with_name("RESULTS.md").write_text(out + "\n", encoding="utf-8")
        print("\nwrote benchmarks/RESULTS.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
