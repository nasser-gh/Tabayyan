"""Differential validation of the Saudi National ID checksum.

Tabayyan's `saudi_id_is_valid` is cross-checked against an independent,
widely-used community implementation:

    alhazmy13/Saudi-ID-Validator  (MIT)
    algorithm credit: Abdul-Aziz Al-Oraij  (http://aziz.oraij.com)
    https://github.com/alhazmy13/Saudi-ID-Validator

The function below is a faithful re-implementation of that project's
`check()` used purely as a test oracle. Agreement across a large random
sample is strong evidence our validator matches the de-facto community
algorithm (it is still not an authoritative government spec — see
REFERENCES.md).
"""
import random

from tabayyan.checksums import saudi_id_is_valid


def _oracle_check(identifier: str):
    """Re-implementation of alhazmy13/Saudi-ID-Validator check() (MIT)."""
    if not identifier.isdigit() or len(identifier) != 10 or identifier[0] not in ("1", "2"):
        return -1
    checksum = 0
    for digit, num in enumerate(identifier):
        num = int(num)
        checksum += sum(map(int, str(num * 2))) if digit % 2 == 0 else num
    return identifier[0] if checksum % 10 == 0 else -1


def _oracle_valid(identifier: str) -> bool:
    return _oracle_check(identifier) != -1


def test_matches_community_oracle_random():
    rng = random.Random(0)
    for _ in range(50000):
        s = "".join(str(rng.randint(0, 9)) for _ in range(10))
        assert saudi_id_is_valid(s) == _oracle_valid(s), s


def test_matches_community_oracle_edges():
    for e in ["", "1", "0000000000", "3333333333", "12345678901", "aaaaaaaaaa",
              "2000000000", "1000000000"]:
        assert saudi_id_is_valid(e) == _oracle_valid(e), e


def test_oracle_citizen_vs_resident_leading_digit():
    # Sanity: oracle returns the leading digit for valid IDs (1 or 2).
    rng = random.Random(7)
    for leading in ("1", "2"):
        from tabayyan.checksums import saudi_id_check_digit
        body = leading + "".join(str(rng.randint(0, 9)) for _ in range(8))
        full = body + str(saudi_id_check_digit(body))
        assert _oracle_check(full) == leading
        assert saudi_id_is_valid(full)
