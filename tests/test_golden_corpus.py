"""Golden regression test.

Locks the engine's detections on a fixed synthetic corpus. If a code change
alters what is detected (type, value, or span) for any case, this fails —
forcing the change to be conscious and the corpus to be regenerated with
`python -m tests.golden._generate`.
"""
import json
from pathlib import Path

import pytest

from tabayyan import DetectionEngine

_CORPUS = json.loads(
    (Path(__file__).parent / "golden" / "detections.json").read_text(encoding="utf-8")
)
_engine = DetectionEngine()


@pytest.mark.parametrize("case", _CORPUS["cases"], ids=[c["name"] for c in _CORPUS["cases"]])
def test_golden_detection(case):
    got = [
        {"type": m.entity_type.value, "value": m.value, "start": m.start, "end": m.end}
        for m in _engine.scan(case["text"])
    ]
    assert got == case["detections"], (
        f"detection drift on {case['name']!r}; if intentional, regenerate with "
        "`python -m tests.golden._generate`"
    )
