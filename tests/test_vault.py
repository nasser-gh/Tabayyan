import os
import random
import stat

import pytest

pytest.importorskip("cryptography")  # encrypted vault needs tabayyan[crypto]

from tabayyan import (  # noqa: E402
    RedactionMode, decrypt_vault, encrypt_vault, load_vault, restore,
    save_vault, scan_and_redact,
)
from tests.synthetic import make_national_id  # noqa: E402

VAULT = {"<SAUDI_NATIONAL_ID_1>": "1158813996", "<EMAIL_1>": "a@b.com"}


def test_round_trip():
    blob = encrypt_vault(VAULT, "correct horse battery staple")
    assert decrypt_vault(blob, "correct horse battery staple") == VAULT


def test_ciphertext_hides_plaintext():
    blob = encrypt_vault(VAULT, "pw")
    assert b"1158813996" not in blob and b"a@b.com" not in blob


def test_wrong_password_raises():
    blob = encrypt_vault(VAULT, "right")
    with pytest.raises(ValueError):
        decrypt_vault(blob, "wrong")


def test_tampered_blob_raises():
    blob = bytearray(encrypt_vault(VAULT, "pw"))
    blob[-5] ^= 0x01  # flip a bit in the token
    with pytest.raises(ValueError):
        decrypt_vault(bytes(blob), "pw")


def test_empty_password_rejected():
    with pytest.raises(ValueError):
        encrypt_vault(VAULT, "")


def test_two_encryptions_differ_but_both_decrypt():
    a = encrypt_vault(VAULT, "pw")
    b = encrypt_vault(VAULT, "pw")
    assert a != b  # random salt + Fernet IV
    assert decrypt_vault(a, "pw") == decrypt_vault(b, "pw") == VAULT


def test_save_load_file_roundtrip_and_perms(tmp_path):
    p = tmp_path / "vault.enc"
    save_vault(VAULT, str(p), "pw")
    assert load_vault(str(p), "pw") == VAULT
    mode = stat.S_IMODE(os.stat(p).st_mode)
    assert mode == 0o600  # owner-only


def test_end_to_end_tokenize_persist_restore(tmp_path):
    nid = make_national_id(random.Random(600), "1")
    result = scan_and_redact(f"id {nid}", RedactionMode.TOKENIZE)
    p = tmp_path / "v.enc"
    save_vault(result.vault, str(p), "s3cret")
    # later / elsewhere: load the vault and restore the original text
    recovered = load_vault(str(p), "s3cret")
    assert restore(result.text, recovered) == f"id {nid}"
