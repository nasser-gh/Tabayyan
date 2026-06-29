"""NDMO data classification mapping.

Saudi Arabia's National Data Management Office (NDMO) Data Classification
Policy defines four sensitivity levels. Mapping each detected entity to a
level turns a redaction pass into classification evidence: the highest level
present tells a reviewer how the document must be handled and whether a
cross-border transfer is permitted under PDPL.

The mapping below is a **practical default**, not legal advice — an
organisation's own data-classification matrix takes precedence. Levels and
the per-category mapping are easy to override.

Levels (most to least sensitive):
  TOP_SECRET  سري للغاية   national-security / gravest-harm data
  SECRET      سري          serious harm if disclosed — health data sits here
  CONFIDENTIAL سري/مقيّد    limited harm — most PII (IDs, financial, contact)
  PUBLIC      عام          no harm from disclosure
"""
from __future__ import annotations

from enum import Enum

from .entities import Category, Match


class Classification(str, Enum):
    PUBLIC = "public"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"
    TOP_SECRET = "top_secret"


# Severity order for "highest classification present" comparisons.
_RANK = {
    Classification.PUBLIC: 0,
    Classification.CONFIDENTIAL: 1,
    Classification.SECRET: 2,
    Classification.TOP_SECRET: 3,
}

# Arabic label for each level (audit/reporting convenience).
LABEL_AR = {
    Classification.PUBLIC: "عام",
    Classification.CONFIDENTIAL: "سري/مقيّد",
    Classification.SECRET: "سري",
    Classification.TOP_SECRET: "سري للغاية",
}

# Default category -> classification. Health is SECRET (sensitive personal
# data under PDPL); identifiers/financial/contact/person are CONFIDENTIAL;
# org identifiers and network info default to PUBLIC; THREAT is not personal
# data and carries no classification on its own.
CATEGORY_CLASSIFICATION: dict[Category, Classification] = {
    Category.SENSITIVE_HEALTH: Classification.SECRET,
    Category.NATIONAL_IDENTIFIER: Classification.CONFIDENTIAL,
    Category.FINANCIAL: Classification.CONFIDENTIAL,
    Category.CONTACT: Classification.CONFIDENTIAL,
    Category.PERSON: Classification.CONFIDENTIAL,
    Category.ORGANISATION: Classification.PUBLIC,
    Category.NETWORK: Classification.PUBLIC,
    Category.THREAT: Classification.PUBLIC,
}


def classify_category(category: Category) -> Classification:
    return CATEGORY_CLASSIFICATION.get(category, Classification.CONFIDENTIAL)


def classify(matches: list[Match]) -> Classification | None:
    """Return the highest NDMO classification among detected entities, or
    None when nothing classifiable was found."""
    levels = [classify_category(m.category) for m in matches]
    if not levels:
        return None
    return max(levels, key=lambda c: _RANK[c])


def classification_summary(matches: list[Match]) -> dict[str, int]:
    """Count of detected entities per classification level (level -> count)."""
    out: dict[str, int] = {}
    for m in matches:
        key = classify_category(m.category).value
        out[key] = out.get(key, 0) + 1
    return out
