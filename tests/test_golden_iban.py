"""Golden IBAN vectors.

These are public, universally-published example IBANs (ISO 13616 /
Wikipedia / SAMA documentation), used everywhere as test data — not real
accounts. They validate the mod-97 engine and the Saudi detector.
"""
from tabayyan import DetectionEngine, EntityType
from tabayyan.checksums import iban_mod97_is_valid

engine = DetectionEngine()

VALID = [
    "SA0380000000608010167519",  # canonical Saudi example
    "GB82WEST12345698765432",    # ISO/Wikipedia example
    "DE89370400440532013000",    # German example
    "FR1420041010050500013M02606",
]
INVALID = [
    "SA0380000000608010167518",  # last digit mutated
    "GB82WEST12345698765431",
    "SA0000000000000000000000",
]


def test_mod97_accepts_public_examples():
    for ib in VALID:
        assert iban_mod97_is_valid(ib), ib


def test_mod97_rejects_mutated():
    for ib in INVALID:
        assert not iban_mod97_is_valid(ib), ib


def test_engine_detects_saudi_example_only():
    # The Saudi detector fires for the SA example...
    ms = engine.scan("transfer to SA0380000000608010167519 today")
    assert EntityType.SAUDI_IBAN in {m.entity_type for m in ms}
    # ...but not for a (valid) German IBAN — it is Saudi-specific by design.
    ms2 = engine.scan("transfer to DE89370400440532013000 today")
    assert EntityType.SAUDI_IBAN not in {m.entity_type for m in ms2}
