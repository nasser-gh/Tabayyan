"""Golden credit-card vectors.

Official card-network TEST numbers, published by the networks and payment
processors (Stripe/PayPal/Adyen docs). They are not real cards. All are
Luhn-valid; the detector must classify them as credit_card.
"""
from tabayyan import DetectionEngine, EntityType
from tabayyan.checksums import luhn_is_valid

engine = DetectionEngine()

OFFICIAL_TEST_PANS = {
    "visa_16": "4111111111111111",
    "visa_16b": "4012888888881881",
    "mastercard_a": "5555555555554444",
    "mastercard_b": "5105105105105100",
    "amex_a": "378282246310005",
    "amex_b": "371449635398431",
    "discover": "6011111111111117",
    "jcb": "3530111333300000",
    "diners": "30569309025904",
}


def test_official_test_pans_are_luhn_valid():
    for name, pan in OFFICIAL_TEST_PANS.items():
        assert luhn_is_valid(pan), name


def test_engine_detects_official_test_pans():
    for name, pan in OFFICIAL_TEST_PANS.items():
        ms = engine.scan(f"card on file {pan} exp 12/30")
        assert EntityType.CREDIT_CARD in {m.entity_type for m in ms}, name


def test_luhn_invalid_variants_rejected():
    for pan in OFFICIAL_TEST_PANS.values():
        bad = pan[:-1] + str((int(pan[-1]) + 1) % 10)
        assert not luhn_is_valid(bad), bad
