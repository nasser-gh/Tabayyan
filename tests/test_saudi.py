import random

from tabayyan import DetectionEngine, EntityType
from tabayyan.entities import Confidence
from tests.synthetic import (
    make_iban, make_invalid_iban, make_invalid_national_id, make_landline, make_mobile,
    make_national_address, make_national_id, make_passport, make_unified_number, make_vat,
)

engine = DetectionEngine()


def _types(matches):
    return {m.entity_type for m in matches}


def test_detects_valid_national_id():
    nid = make_national_id(random.Random(10), "1")
    matches = engine.scan(f"Patient national ID is {nid}.")
    assert EntityType.SAUDI_NATIONAL_ID in _types(matches)
    nm = next(m for m in matches if m.entity_type == EntityType.SAUDI_NATIONAL_ID)
    assert nm.confidence == Confidence.HIGH


def test_iqama_classified_separately():
    iqama = make_national_id(random.Random(11), "2")
    assert EntityType.SAUDI_IQAMA in _types(engine.scan(f"Resident iqama {iqama}"))


def test_invalid_national_id_not_detected():
    bad = make_invalid_national_id(random.Random(12), "1")
    assert EntityType.SAUDI_NATIONAL_ID not in _types(engine.scan(f"value {bad} here"))


def test_detects_valid_iban_with_spaces():
    iban = make_iban(random.Random(13))
    spaced = " ".join(iban[i:i + 4] for i in range(0, len(iban), 4))
    assert EntityType.SAUDI_IBAN in _types(engine.scan(f"Account: {spaced}"))


def test_invalid_iban_not_detected():
    bad = make_invalid_iban(random.Random(14))
    assert EntityType.SAUDI_IBAN not in _types(engine.scan(f"Account: {bad}"))


def test_mobile_formats():
    rng = random.Random(15)
    for fmt in ("+966", "966", "0"):
        assert EntityType.SAUDI_MOBILE in _types(engine.scan(f"call {make_mobile(rng, fmt)} now"))


def test_mobile_international_00966_prefix():
    rng = random.Random(115)
    intl = "00966" + make_mobile(rng, "966")[3:]  # 00966 5XXXXXXXX
    assert EntityType.SAUDI_MOBILE in _types(engine.scan(f"call {intl} now"))


def test_arabic_indic_digits_in_national_id():
    nid = make_national_id(random.Random(16), "1")
    arabic = nid.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))
    assert EntityType.SAUDI_NATIONAL_ID in _types(engine.scan(f"الهوية {arabic}"))


def test_cr_requires_context():
    from tabayyan.checksums import saudi_id_is_valid
    rng = random.Random(17)
    # Pick a 10-digit value that is NOT a valid National ID, so CR is the
    # sole claimant over the span (otherwise the engine correctly prefers
    # the higher-confidence National ID match).
    while True:
        ten = "1010" + "".join(str(rng.randint(0, 9)) for _ in range(6))
        if not saudi_id_is_valid(ten):
            break
    assert EntityType.SAUDI_CR not in _types(engine.scan(f"ref {ten}"))
    cr = [m for m in engine.scan(f"Commercial Registration {ten}")
          if m.entity_type == EntityType.SAUDI_CR]
    assert cr and cr[0].confidence == Confidence.LOW


def test_mrn_is_health_category():
    mrn = [m for m in engine.scan("MRN: A1234567")
           if m.entity_type == EntityType.MEDICAL_RECORD_NUMBER]
    assert mrn and mrn[0].category.value == "sensitive_health"


# --- new Saudi entities (PR A) ---

def test_landline_formats_standalone():
    rng = random.Random(200)
    for fmt in ("+966", "966", "0"):
        assert EntityType.SAUDI_LANDLINE in _types(engine.scan(f"office {make_landline(rng, fmt)} ext 4"))


def test_landline_not_confused_with_mobile():
    rng = random.Random(201)
    t = _types(engine.scan(f"call {make_mobile(rng)} or {make_landline(rng)}"))
    assert EntityType.SAUDI_MOBILE in t and EntityType.SAUDI_LANDLINE in t


def test_vat_requires_context():
    vat = make_vat(random.Random(202))
    assert EntityType.SAUDI_VAT in _types(engine.scan(f"VAT no {vat}"))
    assert EntityType.SAUDI_VAT in _types(engine.scan(f"الرقم الضريبي {vat}"))
    # bare 15-digit run with no tax context must not be flagged as VAT
    assert EntityType.SAUDI_VAT not in _types(engine.scan(f"order {vat} shipped"))


def test_passport_requires_context():
    pp = make_passport(random.Random(203))
    assert EntityType.SAUDI_PASSPORT in _types(engine.scan(f"passport {pp}"))
    assert EntityType.SAUDI_PASSPORT in _types(engine.scan(f"رقم الجواز {pp}"))
    assert EntityType.SAUDI_PASSPORT not in _types(engine.scan(f"code {pp} ok"))


def test_border_number_requires_context():
    rng = random.Random(204)
    num = "3" + "".join(str(rng.randint(0, 9)) for _ in range(9))  # 10 digits, not a valid NID
    assert EntityType.SAUDI_BORDER_NUMBER in _types(engine.scan(f"رقم الحدود {num}"))
    assert EntityType.SAUDI_BORDER_NUMBER in _types(engine.scan(f"border number {num}"))
    assert EntityType.SAUDI_BORDER_NUMBER not in _types(engine.scan(f"ref {num}"))


def test_national_address_requires_context():
    addr = make_national_address(random.Random(205))
    assert EntityType.SAUDI_NATIONAL_ADDRESS in _types(engine.scan(f"national address {addr}"))
    assert EntityType.SAUDI_NATIONAL_ADDRESS in _types(engine.scan(f"العنوان الوطني {addr}"))
    assert EntityType.SAUDI_NATIONAL_ADDRESS not in _types(engine.scan(f"sku {addr}"))


def test_unified_number_requires_context():
    num = make_unified_number(random.Random(206))
    assert EntityType.SAUDI_UNIFIED_NUMBER in _types(engine.scan(f"الرقم الموحد {num}"))
    assert EntityType.SAUDI_UNIFIED_NUMBER not in _types(engine.scan(f"qty {num}"))


def test_unified_number_700_substring_does_not_self_trigger():
    # a value containing "700" as a digit substring must not satisfy its own
    # context gate (the \b700\b trigger is for the colloquial "700 number")
    assert EntityType.SAUDI_UNIFIED_NUMBER not in _types(engine.scan("ref 7001234567 filed"))
    # but the standalone phrase still triggers
    assert EntityType.SAUDI_UNIFIED_NUMBER in _types(engine.scan("700 number 7234567890"))


def test_arabic_indic_digits_in_new_entities():
    vat = make_vat(random.Random(207))
    arabic = vat.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))
    assert EntityType.SAUDI_VAT in _types(engine.scan(f"الرقم الضريبي {arabic}"))
