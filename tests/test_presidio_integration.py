"""Presidio integration tests (require the `presidio` extra; skipped otherwise).

Tested at the recognizer + registry level — this proves the integration
contract (RecognizerResult shape, entity mapping, score mapping, filtering,
registration) without needing a downloaded spaCy model.
"""
import random

import pytest

pytest.importorskip("presidio_analyzer")

from presidio_analyzer import RecognizerRegistry, RecognizerResult  # noqa: E402

from tabayyan import DetectionEngine  # noqa: E402
from tabayyan.integrations.presidio import (  # noqa: E402
    ENTITY_MAP, SaudiRecognizer, get_saudi_recognizers, register_saudi_recognizers,
)
from tests.synthetic import make_iban, make_national_id  # noqa: E402


def test_recognizer_returns_recognizer_results():
    nid = make_national_id(random.Random(60), "1")
    rec = SaudiRecognizer()
    out = rec.analyze(f"national ID {nid}", entities=rec.supported_entities, nlp_artifacts=None)
    assert out and all(isinstance(r, RecognizerResult) for r in out)
    hit = next(r for r in out if r.entity_type == "SA_NATIONAL_ID")
    assert hit.score == 0.95


def test_iban_and_iqama_entities():
    rng = random.Random(61)
    iban = make_iban(rng)
    iqama = make_national_id(rng, "2")
    rec = SaudiRecognizer()
    text = f"iqama {iqama} account {iban}"
    types = {r.entity_type for r in rec.analyze(text, entities=rec.supported_entities, nlp_artifacts=None)}
    assert "SA_IQAMA" in types
    assert "SA_IBAN" in types


def test_entity_filtering():
    rng = random.Random(62)
    nid = make_national_id(rng, "1")
    iban = make_iban(rng)
    rec = SaudiRecognizer()
    text = f"id {nid} iban {iban}"
    only = rec.analyze(text, entities=["SA_IBAN"], nlp_artifacts=None)
    assert {r.entity_type for r in only} == {"SA_IBAN"}


def test_supported_entities_are_mapped_names():
    rec = SaudiRecognizer()
    assert "SA_NATIONAL_ID" in rec.supported_entities
    assert "MEDICAL_RECORD_NUMBER" in rec.supported_entities
    # all supported entities come from the public ENTITY_MAP
    assert set(rec.supported_entities) <= set(ENTITY_MAP.values())


def test_metadata_carries_tabayyan_confidence_and_category():
    nid = make_national_id(random.Random(63), "1")
    rec = SaudiRecognizer()
    r = rec.analyze(f"id {nid}", entities=["SA_NATIONAL_ID"], nlp_artifacts=None)[0]
    md = r.recognition_metadata
    assert md["tabayyan_confidence"] == "high"
    assert md["tabayyan_category"] == "national_identifier"


def test_register_adds_to_registry():
    registry = RecognizerRegistry()
    register_saudi_recognizers(registry)
    names = {r.name for r in registry.recognizers}
    assert "TabayyanSaudiRecognizer" in names


def test_parity_with_standalone_engine():
    # The recognizer must detect exactly the same Saudi/Arabic spans the
    # standalone engine does (mapped to Presidio names).
    rng = random.Random(64)
    nid = make_national_id(rng, "1")
    iban = make_iban(rng)
    text = f"اسم المريض عبدالله القحطاني الهوية {nid} الآيبان {iban}"

    standalone = DetectionEngine().scan(text)
    standalone_saudi = {
        (ENTITY_MAP[m.entity_type], m.start, m.end)
        for m in standalone if m.entity_type in ENTITY_MAP
    }
    rec = SaudiRecognizer()
    pres = {(r.entity_type, r.start, r.end)
            for r in rec.analyze(text, entities=rec.supported_entities, nlp_artifacts=None)}
    assert standalone_saudi == pres


def test_domain_recognizer_with_watchlist():
    recs = get_saudi_recognizers(watchlist=["example.com"])
    assert len(recs) == 2
    dom = recs[1]
    out = dom.analyze("login at ex\u0430mple.com", entities=["SUSPICIOUS_DOMAIN"], nlp_artifacts=None)
    assert out and out[0].entity_type == "SUSPICIOUS_DOMAIN"
