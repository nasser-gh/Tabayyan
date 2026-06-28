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
    make_mobile, make_national_id,
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

    rng.shuffle(s)
    return s


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
    table = render(stats)
    comparison = render_comparison(stats, naive)

    header = (f"# Benchmark results\n\nSynthetic corpus, seed={args.seed}, "
              f"{len(corpus)} samples (positives + hard negatives).\n\n")
    out = header + table + "\n\n" + comparison
    print(out)
    if args.write:
        Path(__file__).with_name("RESULTS.md").write_text(out + "\n", encoding="utf-8")
        print("\nwrote benchmarks/RESULTS.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
