"""Core data model shared across detectors and the engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Confidence(str, Enum):
    HIGH = "high"      # passes a published checksum
    MEDIUM = "medium"  # strong format match, no checksum available
    LOW = "low"        # format-only; needs contextual confirmation


class Category(str, Enum):
    NATIONAL_IDENTIFIER = "national_identifier"
    FINANCIAL = "financial"
    CONTACT = "contact"
    SENSITIVE_HEALTH = "sensitive_health"
    NETWORK = "network"
    ORGANISATION = "organisation"
    THREAT = "threat"
    PERSON = "person"


class EntityType(str, Enum):
    SAUDI_NATIONAL_ID = "saudi_national_id"
    SAUDI_IQAMA = "saudi_iqama"
    SAUDI_IBAN = "saudi_iban"
    SAUDI_CR = "saudi_cr"
    SAUDI_MOBILE = "saudi_mobile"
    MEDICAL_RECORD_NUMBER = "medical_record_number"
    EMAIL = "email"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    SUSPICIOUS_DOMAIN = "suspicious_domain"
    ARABIC_NAME = "arabic_name"
    CUSTOM = "custom"


@dataclass(frozen=True)
class Match:
    entity_type: EntityType
    category: Category
    confidence: Confidence
    start: int
    end: int
    value: str
    detector: str = ""
    notes: str = field(default="")
    label: str = ""  # human label for custom entities; falls back to type

    @property
    def length(self) -> int:
        return self.end - self.start

    def redacted(self) -> str:
        name = self.label or self.entity_type.value
        return f"[{name.upper()}]"

    def to_dict(self) -> dict:
        return {
            "entity_type": self.entity_type.value,
            "category": self.category.value,
            "confidence": self.confidence.value,
            "start": self.start,
            "end": self.end,
            "value": self.value,
            "detector": self.detector,
            "notes": self.notes,
            "label": self.label,
        }
