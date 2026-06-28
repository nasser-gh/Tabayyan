"""Differential validation against python-stdnum (MIT/LGPL), an independent,
widely-used numeric-standards library. Dev-only: skipped if not installed.

Cross-checks:
  * Luhn  — tabayyan.checksums.luhn_is_valid vs stdnum.luhn.is_valid
  * IBAN  — tabayyan.checksums.iban_mod97_is_valid vs stdnum.iban.is_valid
            on generated Saudi IBANs (valid and mutated).
"""
import random

import pytest

stdnum = pytest.importorskip("stdnum")
from stdnum import iban as st_iban   # noqa: E402
from stdnum import luhn as st_luhn   # noqa: E402

from tabayyan.checksums import (  # noqa: E402
    iban_check_digits, iban_mod97_is_valid, luhn_is_valid,
)
from tests.synthetic import make_iban  # noqa: E402


def test_luhn_matches_stdnum_random():
    rng = random.Random(0)
    for _ in range(20000):
        n = "".join(str(rng.randint(0, 9)) for _ in range(rng.randint(12, 19)))
        assert luhn_is_valid(n) == st_luhn.is_valid(n), n


def test_iban_matches_stdnum_on_generated_saudi():
    rng = random.Random(1)
    for _ in range(5000):
        ib = make_iban(rng)            # mod-97-valid SA IBAN
        assert iban_mod97_is_valid(ib)
        assert st_iban.is_valid(ib), ib


def test_iban_matches_stdnum_on_mutations():
    rng = random.Random(2)
    for _ in range(5000):
        ib = make_iban(rng)
        # mutate one BBAN digit -> both must reject
        i = rng.randint(4, 23)
        bad = ib[:i] + str((int(ib[i]) + 1) % 10) + ib[i + 1:]
        assert iban_mod97_is_valid(bad) == st_iban.is_valid(bad) == False  # noqa: E712


def test_iban_check_digits_match_stdnum():
    rng = random.Random(3)
    for _ in range(2000):
        bban = "".join(str(rng.randint(0, 9)) for _ in range(20))
        ib = "SA" + iban_check_digits("SA", bban) + bban
        assert st_iban.is_valid(ib), ib
