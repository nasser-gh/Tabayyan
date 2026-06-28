import random

from tabayyan import DetectionEngine, EntityType
from tests.synthetic import make_credit_card

engine = DetectionEngine()


def _types(matches):
    return {m.entity_type for m in matches}


def test_email():
    assert EntityType.EMAIL in _types(engine.scan("reach me at analyst@example.gov.sa please"))


def test_valid_credit_card():
    pan = make_credit_card(random.Random(20), 16)
    assert EntityType.CREDIT_CARD in _types(engine.scan(f"card {pan}"))


def test_non_luhn_number_not_card():
    assert EntityType.CREDIT_CARD not in _types(engine.scan("order number 1234567812345678"))


def test_ipv4_and_ipv6():
    assert EntityType.IP_ADDRESS in _types(engine.scan("host 192.168.10.5"))
    assert EntityType.IP_ADDRESS in _types(engine.scan("host 2001:db8::1"))


def test_invalid_ipv4_rejected():
    assert EntityType.IP_ADDRESS not in _types(engine.scan("version 999.999.1.1"))
