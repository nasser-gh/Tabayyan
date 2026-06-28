import random

from tabayyan import DetectionEngine, EntityType
from tests.synthetic import make_national_id

engine = DetectionEngine()


def test_overlap_resolution_prefers_high_confidence():
    # A checksum-valid national ID is also a bare 10-digit run; engine must
    # keep exactly one match over that span.
    nid = make_national_id(random.Random(30), "1")
    matches = engine.scan(f"id {nid}")
    spanning = [m for m in matches if m.value == nid or nid in m.value]
    assert len(spanning) == 1
    assert spanning[0].entity_type == EntityType.SAUDI_NATIONAL_ID


def test_matches_sorted_by_position():
    nid = make_national_id(random.Random(31), "1")
    matches = engine.scan(f"email a@b.com then id {nid}")
    starts = [m.start for m in matches]
    assert starts == sorted(starts)


def test_clean_text_no_matches():
    assert engine.scan("the quick brown fox jumps over the lazy dog") == []
