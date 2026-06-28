import random

from tabayyan import RedactionMode, restore, scan_and_redact
from tests.synthetic import make_national_id


def test_tokenize_repeats_share_token():
    nid = make_national_id(random.Random(80), "1")
    r = scan_and_redact(f"id {nid} again {nid}", RedactionMode.TOKENIZE)
    tokens = [i.replacement for i in r.items]
    assert len(set(tokens)) == 1  # same value -> same token


def test_tokenize_restore_roundtrip():
    rng = random.Random(81)
    a, b = make_national_id(rng, "1"), make_national_id(rng, "1")
    text = f"first {a}, second {b}, first-again {a}"
    r = scan_and_redact(text, RedactionMode.TOKENIZE)
    assert a not in r.text and b not in r.text
    assert restore(r.text, r.vault) == text


def test_restore_handles_double_digit_token_indices():
    # 12 distinct values -> tokens _1.._12; restore must not corrupt _1 vs _12
    rng = random.Random(82)
    vals = [make_national_id(rng, "1") for _ in range(12)]
    text = " ".join(f"v{i}={vals[i]}" for i in range(12))
    r = scan_and_redact(text, RedactionMode.TOKENIZE)
    assert restore(r.text, r.vault) == text


def test_tokenize_restore_with_arabic_indic_digits():
    # The vault must store the ORIGINAL span (Arabic digits), not the
    # normalized ASCII value, so restore reproduces the source exactly.
    s = "الهوية ١١٥٨٨١٣٩٩٦"
    r = scan_and_redact(s, RedactionMode.TOKENIZE)
    assert "١١٥٨٨١٣٩٩٦" not in r.text
    assert restore(r.text, r.vault) == s
