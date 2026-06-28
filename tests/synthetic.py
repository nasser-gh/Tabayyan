"""Synthetic generators. Every value is fabricated to satisfy/fail a checksum.
Nothing here is real, issued, or traceable to any person or organisation.
"""
from __future__ import annotations

import random

from tabayyan.checksums import iban_check_digits, luhn_check_digit, saudi_id_check_digit


def make_national_id(rng: random.Random, leading: str = "1") -> str:
    body = leading + "".join(str(rng.randint(0, 9)) for _ in range(8))
    return body + str(saudi_id_check_digit(body))


def make_invalid_national_id(rng: random.Random, leading: str = "1") -> str:
    valid = make_national_id(rng, leading)
    return valid[:-1] + str((int(valid[-1]) + 1) % 10)


def make_iban(rng: random.Random) -> str:
    bban = "".join(str(rng.randint(0, 9)) for _ in range(20))
    return "SA" + iban_check_digits("SA", bban) + bban


def make_invalid_iban(rng: random.Random) -> str:
    valid = make_iban(rng)
    return valid[:2] + str((int(valid[2]) + 1) % 10) + valid[3:]


def make_credit_card(rng: random.Random, length: int = 16) -> str:
    body = "".join(str(rng.randint(0, 9)) for _ in range(length - 1))
    return body + str(luhn_check_digit(body))


def make_mobile(rng: random.Random, fmt: str = "+966") -> str:
    rest = "".join(str(rng.randint(0, 9)) for _ in range(8))
    if fmt == "+966":
        return "+9665" + rest
    if fmt == "966":
        return "9665" + rest
    return "05" + rest
