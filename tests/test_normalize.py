import random

from tabayyan import DetectionEngine, EntityType, RedactionMode, scan_and_redact
from tabayyan.normalize import normalize
from tests.synthetic import make_credit_card, make_iban, make_national_id

engine = DetectionEngine()
ZWSP = "​"   # zero-width space
RLM = "‏"    # right-to-left mark (bidi control)


def _types(matches):
    return {m.entity_type for m in matches}


# --- normalize() unit behaviour ---

def test_ascii_is_identity():
    n = normalize("National ID 1010000009 ok")
    assert n.text == "National ID 1010000009 ok"
    assert n.map_span(0, 4) == (0, 4)


def test_strips_zero_width_and_folds_digits():
    n = normalize(f"a{ZWSP}١٢٣")
    assert n.text == "a123"


def test_map_span_covers_deleted_invisibles():
    original = f"1{ZWSP}2"
    n = normalize(original)
    assert n.text == "12"
    # the 2-char clean run maps back over the zero-width in the middle
    assert n.map_span(0, 2) == (0, 3)


# --- evasion is defeated end to end ---

def test_zero_width_split_national_id_still_detected():
    nid = make_national_id(random.Random(300), "1")
    evasive = nid[:5] + ZWSP + nid[5:]
    matches = engine.scan(f"id {evasive}")
    assert EntityType.SAUDI_NATIONAL_ID in _types(matches)
    # value is the clean ASCII id, not the split form
    nm = next(m for m in matches if m.entity_type == EntityType.SAUDI_NATIONAL_ID)
    assert nm.value == nid


def test_redaction_removes_original_span_including_invisible():
    nid = make_national_id(random.Random(301), "1")
    evasive = nid[:4] + ZWSP + nid[4:]
    result = scan_and_redact(f"id {evasive} end", RedactionMode.MASK)
    assert "[SAUDI_NATIONAL_ID]" in result.text
    assert nid not in result.text
    assert ZWSP not in result.text          # invisible was inside the redacted span
    assert result.text.endswith("end")       # surrounding text intact


def test_bidi_control_inside_iban_detected():
    iban = make_iban(random.Random(302))
    evasive = iban[:6] + RLM + iban[6:]
    assert EntityType.SAUDI_IBAN in _types(engine.scan(f"IBAN {evasive}"))


def test_arabic_indic_digits_reach_generic_detectors():
    # credit card detector lives in generic.py and never folded digits itself;
    # central normalization now extends Arabic-Indic robustness to it.
    card = make_credit_card(random.Random(303))
    arabic = card.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))
    assert EntityType.CREDIT_CARD in _types(engine.scan(f"card {arabic}"))


def test_fullwidth_digits_national_id():
    nid = make_national_id(random.Random(304), "1")
    full = nid.translate(str.maketrans("0123456789", "０１２３４５６７８９"))
    assert EntityType.SAUDI_NATIONAL_ID in _types(engine.scan(f"id {full}"))


def test_normalization_can_be_disabled():
    nid = make_national_id(random.Random(305), "1")
    evasive = nid[:5] + ZWSP + nid[5:]
    raw_engine = DetectionEngine(normalize_input=False)
    assert EntityType.SAUDI_NATIONAL_ID not in _types(raw_engine.scan(f"id {evasive}"))
