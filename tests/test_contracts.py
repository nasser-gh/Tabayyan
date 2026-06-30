"""Contract tests — invariants every detector must satisfy.

Instead of bespoke tests per detector, these run the same checks across the
whole default set, so a new detector (including a third-party one) is held to
the same bar: valid spans, proper enum types, determinism, and no crash on
arbitrary Unicode. This is what makes the detector interface a real contract.
"""
import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tabayyan.detectors import DEFAULT_DETECTORS
from tabayyan.entities import Category, Confidence, EntityType, Match
from tests.synthetic import make_iban, make_mobile, make_national_id, make_vat

_rng = random.Random(7)
# A rich text that makes several detectors fire, plus empty / whitespace /
# unicode edge inputs.
_RICH = (
    f"Patient ID {make_national_id(_rng, '1')}, IBAN {make_iban(_rng)}, "
    f"call {make_mobile(_rng, '+966')}, VAT no {make_vat(_rng)}, "
    "email a@b.example, ip 10.0.0.5, الاسم محمد القحطاني"
)
SAMPLES = ["", "   ", "nothing to see", _RICH, "٠١٢٣٤٥٦٧٨٩", "​‮ mixed ﻿"]

DETECTORS = DEFAULT_DETECTORS
IDS = [type(d).__name__ for d in DETECTORS]


@pytest.mark.parametrize("det", DETECTORS, ids=IDS)
def test_detector_output_contract(det):
    for text in SAMPLES:
        matches = list(det.detect(text))
        for m in matches:
            assert isinstance(m, Match)
            assert isinstance(m.entity_type, EntityType)
            assert isinstance(m.category, Category)
            assert isinstance(m.confidence, Confidence)
            assert isinstance(m.value, str)
            assert 0 <= m.start <= m.end <= len(text), f"{type(det).__name__} span out of bounds"


@pytest.mark.parametrize("det", DETECTORS, ids=IDS)
def test_detector_is_deterministic(det):
    for text in SAMPLES:
        a = [m.to_dict() for m in det.detect(text)]
        b = [m.to_dict() for m in det.detect(text)]
        assert a == b


@pytest.mark.parametrize("det", DETECTORS, ids=IDS)
@settings(max_examples=60, deadline=None)
@given(t=st.text(max_size=120))
def test_detector_never_crashes_and_spans_in_bounds(det, t):
    for m in det.detect(t):
        assert 0 <= m.start <= m.end <= len(t)
        assert isinstance(m.entity_type, EntityType)
