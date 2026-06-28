"""Deterministic, offline checksum primitives.

Pure functions only. Passing a checksum confirms a value is *structurally
valid*, NOT that it was ever issued.
"""
from __future__ import annotations


def luhn_is_valid(number: str) -> bool:
    if not number.isdigit():
        return False
    total = 0
    parity = len(number) % 2
    for i, ch in enumerate(number):
        d = int(ch)
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def luhn_check_digit(number_without_check: str) -> int:
    total = 0
    parity = (len(number_without_check) + 1) % 2
    for i, ch in enumerate(number_without_check):
        d = int(ch)
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - (total % 10)) % 10


def saudi_id_is_valid(value: str) -> bool:
    if len(value) != 10 or not value.isdigit() or value[0] not in ("1", "2"):
        return False
    total = 0
    for i in range(10):
        d = int(value[i])
        if i % 2 == 0:
            d *= 2
            total += d // 10 + d % 10
        else:
            total += d
    return total % 10 == 0


def saudi_id_check_digit(first_nine: str) -> int:
    if len(first_nine) != 9 or not first_nine.isdigit():
        raise ValueError("first_nine must be exactly 9 digits")
    partial = 0
    for i in range(9):
        d = int(first_nine[i])
        if i % 2 == 0:
            d *= 2
            partial += d // 10 + d % 10
        else:
            partial += d
    return (10 - (partial % 10)) % 10


def _iban_to_numeric(iban: str) -> str:
    rearranged = iban[4:] + iban[:4]
    out = []
    for ch in rearranged:
        out.append(ch if ch.isdigit() else str(ord(ch.upper()) - 55))
    return "".join(out)


def iban_mod97_is_valid(iban: str) -> bool:
    iban = iban.replace(" ", "").upper()
    if len(iban) < 5 or not iban[:2].isalpha() or not iban[2:4].isdigit():
        return False
    return int(_iban_to_numeric(iban)) % 97 == 1


def iban_check_digits(country: str, bban: str) -> str:
    trial = country.upper() + "00" + bban.upper()
    return f"{98 - (int(_iban_to_numeric(trial)) % 97):02d}"
