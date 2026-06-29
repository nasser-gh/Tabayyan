import random

from tabayyan import DetectionEngine, EntityType
from tabayyan.entities import Confidence
from tests.synthetic import (
    make_iban, make_invalid_iban, make_invalid_national_id, make_mobile, make_national_id,
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
