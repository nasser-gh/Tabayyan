"""Recall benchmark — how much valid PII do we MISS in messy text?

The precision benchmark (run.py) measures false positives on decoys. This
measures the opposite: take VALID entities (correct checksums) and embed
them in realistic, noisy surroundings, then count how many we still detect.

Noise simulates real-world mess: Arabic-Indic digits, odd spacing, field
labels, punctuation, line breaks, and (for heuristic types) varied trigger
phrasing.

Honest caveat: this is still synthetic. It stresses robustness to formatting
noise; it does NOT model the full distribution of real documents, and for
heuristic types (CR, MRN, Arabic names) recall is intentionally limited by a
precision-first design. Numbers here are a floor/sanity signal, not a promise.

Run:  python benchmarks/recall.py [--write]
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

from tabayyan import DetectionEngine, EntityType
from tests.synthetic import make_iban, make_national_id

N = 400
engine = DetectionEngine()

_AR = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def _noise(rng, s):
    """Wrap a value in messy but well-formed surroundings."""
    pre = rng.choice(["", "  ", "ref:", "الرقم: ", "(", "-", "\t", "value=", "\n"])
    post = rng.choice(["", "  ", ".", ")", ",", "\n", " تم", " filed"])
    return f"{pre}{s}{post}"


def _maybe_arabic_digits(rng, s):
    return s.translate(_AR) if rng.random() < 0.4 else s


def recall_for(rng, n, make_value, target_type, embed):
    hits = 0
    for _ in range(n):
        value = make_value(rng)
        text = embed(rng, value)
        detected = {m.entity_type for m in engine.scan(text)}
        if target_type in detected:
            hits += 1
    return hits, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--seed", type=int, default=2024)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    rows = []

    # National ID — checksum type, with Arabic-digit + spacing noise
    def embed_id(rng, v):
        return _noise(rng, _maybe_arabic_digits(rng, v))
    rows.append(("saudi_national_id",
                 *recall_for(rng, N, lambda r: make_national_id(r, "1"),
                             EntityType.SAUDI_NATIONAL_ID, embed_id)))
    rows.append(("saudi_iqama",
                 *recall_for(rng, N, lambda r: make_national_id(r, "2"),
                             EntityType.SAUDI_IQAMA, embed_id)))

    # IBAN — with/without grouping spaces
    def embed_iban(rng, v):
        if rng.random() < 0.5:
            v = " ".join(v[i:i+4] for i in range(0, len(v), 4))
        return _noise(rng, v)
    rows.append(("saudi_iban",
                 *recall_for(rng, N, make_iban, EntityType.SAUDI_IBAN, embed_iban)))

    # Mobile — three formats + Arabic digits
    def make_mob(r):
        rest = "".join(str(r.randint(0, 9)) for _ in range(8))
        return r.choice([f"+9665{rest}", f"9665{rest}", f"05{rest}"])
    def embed_mob(rng, v):
        return _noise(rng, _maybe_arabic_digits(rng, v))
    rows.append(("saudi_mobile",
                 *recall_for(rng, N, make_mob, EntityType.SAUDI_MOBILE, embed_mob)))

    # MRN — heuristic: varied trigger phrasing (expect lower recall)
    def make_mrn(r):
        return "".join(r.choice("ABCDEFGHJKLMNP0123456789") for _ in range(r.randint(6, 9)))
    def embed_mrn(rng, v):
        trig = rng.choice(["MRN:", "MRN ", "Medical Record No.", "رقم الملف:",
                           "السجل الطبي ", "رقم السجل الطبي:"])
        return _noise(rng, f"{trig} {v}")
    rows.append(("medical_record_number",
                 *recall_for(rng, N, make_mrn, EntityType.MEDICAL_RECORD_NUMBER, embed_mrn)))

    # Arabic names — heuristic: varied triggers/particles (expect lower recall)
    GIVEN = ["عبدالله", "محمد", "فهد", "نورة", "سارة", "عبد العزيز", "خالد", "ريم"]
    FAMILY = ["القحطاني", "الزهراني", "العتيبي", "آل سعود", "الدوسري", "الشمري"]
    def make_name(r):
        return f"{r.choice(GIVEN)} {r.choice(FAMILY)}"
    def embed_name(rng, v):
        trig = rng.choice(["اسم المريض", "المريض", "السيد", "د.", "المراجع", "الطبيب"])
        return _noise(rng, f"{trig} {v}")
    rows.append(("arabic_name",
                 *recall_for(rng, N, make_name, EntityType.ARABIC_NAME, embed_name)))

    # --- Context-free recall for heuristic types: the honest limitation ---
    # Names/MRN without any trigger keyword. Recall here SHOULD be low — the
    # detectors are precision-first and only fire on contextual evidence.
    def make_name_plain(r):
        return f"{r.choice(GIVEN)} {r.choice(FAMILY)}"
    def embed_bare(rng, v):
        return _noise(rng, f"تم تسجيل {v} في النظام")  # no name trigger
    name_cf_hits, _ = recall_for(rng, N, make_name_plain,
                                 EntityType.ARABIC_NAME, embed_bare)

    def embed_mrn_bare(rng, v):
        return _noise(rng, f"الكود {v} مسجل")  # no MRN keyword
    mrn_cf_hits, _ = recall_for(rng, N, make_mrn,
                                EntityType.MEDICAL_RECORD_NUMBER, embed_mrn_bare)

    # Render
    lines = ["# Recall benchmark (noisy synthetic)\n",
             f"seed={args.seed}, {N} samples per type.\n",
             "| Entity type | Detected | Total | Recall |",
             "|---|---:|---:|---:|"]
    for name, hits, total in rows:
        lines.append(f"| {name} | {hits} | {total} | {hits/total:.3f} |")
    lines.append("")
    lines.append("## Context-free recall (heuristic types, no trigger present)")
    lines.append("")
    lines.append("These are the honest limits: with no contextual keyword, "
                 "precision-first detectors miss most/all entities by design.")
    lines.append("")
    lines.append("| Entity type | Detected | Total | Recall | Note |")
    lines.append("|---|---:|---:|---:|---|")
    lines.append(f"| arabic_name (no trigger) | {name_cf_hits} | {N} | "
                 f"{name_cf_hits/N:.3f} | fires only on name particles (عبد/بن/آل) |")
    lines.append(f"| medical_record_number (no keyword) | {mrn_cf_hits} | {N} | "
                 f"{mrn_cf_hits/N:.3f} | requires an MRN keyword by design |")
    lines.append("")
    lines.append("*Interpretation: with context, recall is high; without context, "
                 "heuristic types deliberately stay silent to protect precision. "
                 "Use checksum-backed types (ID/IBAN/mobile) for high-recall needs.*")
    out = "\n".join(lines)
    print(out)
    if args.write:
        Path(__file__).with_name("RECALL.md").write_text(out + "\n", encoding="utf-8")
        print("\nwrote benchmarks/RECALL.md")


if __name__ == "__main__":
    main()
