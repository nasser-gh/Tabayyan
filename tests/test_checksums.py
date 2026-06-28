import random

from tabayyan.checksums import (
    iban_check_digits, iban_mod97_is_valid, luhn_check_digit, luhn_is_valid,
    saudi_id_check_digit, saudi_id_is_valid,
)
from tests.synthetic import make_credit_card, make_iban, make_national_id


def test_luhn_known_vector():
    assert luhn_is_valid("4111111111111111")
    assert not luhn_is_valid("4111111111111112")


def test_luhn_roundtrip():
    rng = random.Random(1)
    for _ in range(200):
        body = "".join(str(rng.randint(0, 9)) for _ in range(15))
        assert luhn_is_valid(body + str(luhn_check_digit(body)))


def test_saudi_id_roundtrip_citizen_and_iqama():
    rng = random.Random(2)
    for leading in ("1", "2"):
        for _ in range(200):
            body = leading + "".join(str(rng.randint(0, 9)) for _ in range(8))
            full = body + str(saudi_id_check_digit(body))
            assert saudi_id_is_valid(full)
            assert not saudi_id_is_valid(full[:-1] + str((int(full[-1]) + 1) % 10))


def test_saudi_id_rejects_bad_leading():
    rng = random.Random(3)
    valid = make_national_id(rng, "1")
    assert not saudi_id_is_valid("3" + valid[1:])


def test_iban_roundtrip():
    rng = random.Random(4)
    for _ in range(200):
        iban = make_iban(rng)
        assert len(iban) == 24 and iban_mod97_is_valid(iban)


def test_iban_check_digits_match():
    rng = random.Random(5)
    bban = "".join(str(rng.randint(0, 9)) for _ in range(20))
    assert iban_mod97_is_valid("SA" + iban_check_digits("SA", bban) + bban)


def test_credit_card_generator_is_luhn_valid():
    rng = random.Random(6)
    for length in (13, 15, 16, 19):
        assert luhn_is_valid(make_credit_card(rng, length))
