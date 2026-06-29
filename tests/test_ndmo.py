import random

from tabayyan import Classification, Guard, classification_summary, classify, scan
from tabayyan.entities import Category, Confidence, EntityType, Match
from tests.synthetic import make_iban, make_national_id

AZURE = "https://contoso.openai.azure.com/v1/chat"


def _match(category):
    return Match(EntityType.CUSTOM, category, Confidence.LOW, 0, 1, "x")


def test_category_levels():
    assert classify([_match(Category.SENSITIVE_HEALTH)]) is Classification.SECRET
    assert classify([_match(Category.NATIONAL_IDENTIFIER)]) is Classification.CONFIDENTIAL
    assert classify([_match(Category.ORGANISATION)]) is Classification.PUBLIC


def test_classify_returns_highest_level():
    matches = [_match(Category.ORGANISATION), _match(Category.SENSITIVE_HEALTH),
               _match(Category.CONTACT)]
    assert classify(matches) is Classification.SECRET


def test_classify_none_when_empty():
    assert classify([]) is None


def test_classification_summary_counts_per_level():
    matches = [_match(Category.NATIONAL_IDENTIFIER), _match(Category.FINANCIAL),
               _match(Category.SENSITIVE_HEALTH)]
    summ = classification_summary(matches)
    assert summ == {"confidential": 2, "secret": 1}


def test_real_scan_classification():
    nid = make_national_id(random.Random(500), "1")
    iban = make_iban(random.Random(501))
    matches = scan(f"id {nid} iban {iban}")
    assert classify(matches) is Classification.CONFIDENTIAL


def test_audit_carries_classification():
    nid = make_national_id(random.Random(502), "1")
    pr = Guard().protect(f"MRN: A1234 and ID {nid}", destination=AZURE)
    # MRN is health -> SECRET should win over the national id (CONFIDENTIAL)
    assert pr.audit.data_classification == "secret"
    assert pr.audit.classification_summary.get("secret", 0) >= 1
    # serializes cleanly into the JSONL audit
    assert "data_classification" in pr.audit.to_json()


def test_audit_classification_none_when_no_pii():
    pr = Guard().protect("the quarterly report is ready", destination=AZURE)
    assert pr.audit.data_classification is None
