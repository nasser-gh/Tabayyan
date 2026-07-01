"""Guard the README's runnable examples.

A reviewer found the quick-start used a National ID that fails the checksum, so
the headline example silently detected nothing. These tests tie the README's
example IDs to the validator and the engine, so an invalid example can't ship.
"""
import re
from pathlib import Path

from tabayyan import scan
from tabayyan.checksums import saudi_id_is_valid
from tabayyan.entities import EntityType

_README = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
_NATIONAL_IDS = sorted(set(re.findall(r"National ID (\d{10})", _README)))


def test_readme_has_national_id_examples():
    assert _NATIONAL_IDS, "expected 'National ID <10 digits>' examples in README"


def test_readme_national_id_examples_pass_checksum():
    bad = [nid for nid in _NATIONAL_IDS if not saudi_id_is_valid(nid)]
    assert not bad, f"README shows checksum-invalid National IDs (won't be detected): {bad}"


def test_readme_national_id_examples_are_detected():
    for nid in _NATIONAL_IDS:
        types = {m.entity_type for m in scan(f"National ID {nid}")}
        assert EntityType.SAUDI_NATIONAL_ID in types, f"README ID {nid} is not detected"
