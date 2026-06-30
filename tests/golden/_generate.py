"""Regenerate the golden detection corpus.

Run this ONLY when a detection change is intentional:

    python -m tests.golden._generate     # rewrites detections.json

It builds a fixed set of synthetic texts (deterministic seeds — no real data),
runs the current engine, and snapshots the detections. `test_golden_corpus.py`
then asserts the engine keeps producing exactly this, so an *unintended*
detection change fails CI and forces a conscious update of this file.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from tabayyan import DetectionEngine
from tabayyan.checksums import luhn_is_valid
from tests.synthetic import (
    make_credit_card, make_iban, make_landline, make_mobile, make_national_address,
    make_national_id, make_passport, make_unified_number, make_vat,
)

rng = random.Random(20240601)
NID = make_national_id(rng, "1")
IQAMA = make_national_id(rng, "2")
IBAN = make_iban(rng)
CARD = make_credit_card(rng, 16)
MOBILE = make_mobile(rng, "+966")
LANDLINE = make_landline(rng, "0")
# Pick a VAT that is NOT coincidentally Luhn-valid, so it is detected as
# saudi_vat (not claimed by the higher-confidence credit_card detector).
VAT = make_vat(rng)
while luhn_is_valid(VAT):
    VAT = make_vat(rng)
PASSPORT = make_passport(rng)
ADDR = make_national_address(rng)
UNIFIED = make_unified_number(rng)
ZWSP = "​"

# (name, text) — each text is fully synthetic. Expected detections are filled
# in by running the engine below.
CASES = [
    ("national_id", f"Patient national ID {NID} on file."),
    ("iqama", f"Iqama no {IQAMA}."),
    ("iban", f"Salary IBAN {IBAN}."),
    ("credit_card", f"Card {CARD} charged."),
    ("mobile", f"Call {MOBILE} after 5pm."),
    ("landline", f"Office line {LANDLINE}."),
    ("email_ip", "Mail a@b.example from 10.0.0.5 today."),
    ("vat_context", f"VAT no {VAT} on the invoice."),
    ("passport_context", f"passport {PASSPORT} expires soon."),
    ("national_address_context", f"national address {ADDR}."),
    ("unified_context", f"الرقم الموحد {UNIFIED}."),
    ("mixed_record", f"Name: patient; ID {NID}; IBAN {IBAN}; phone {MOBILE}."),
    ("evasion_zero_width", f"id {NID[:5]}{ZWSP}{NID[5:]} hidden"),
    ("evasion_arabic_digits", "الهوية "
        + NID.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))),
    ("hard_negative_no_context_vat", f"order {VAT} shipped"),  # 15 digits, no tax ctx
    ("clean", "The quarterly report is ready for review."),
]


def build() -> dict:
    engine = DetectionEngine()
    out = []
    for name, text in CASES:
        dets = [
            {"type": m.entity_type.value, "value": m.value, "start": m.start, "end": m.end}
            for m in engine.scan(text)
        ]
        out.append({"name": name, "text": text, "detections": dets})
    return {"version": 1, "cases": out}


if __name__ == "__main__":
    path = Path(__file__).with_name("detections.json")
    path.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path} ({len(CASES)} cases)")
