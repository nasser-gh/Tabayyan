"""Saudi-specific entity detectors — the differentiator."""
from __future__ import annotations

import re
from typing import Iterable

from ..checksums import iban_mod97_is_valid, saudi_id_is_valid
from ..entities import Category, Confidence, EntityType, Match
from .base import Detector

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def _normalise_digits(text: str) -> str:
    return text.translate(_ARABIC_DIGITS)


class SaudiNationalIdDetector(Detector):
    name = "saudi_national_id"
    _pattern = re.compile(r"(?<!\d)([12]\d{9})(?!\d)")

    def detect(self, text: str) -> Iterable[Match]:
        norm = _normalise_digits(text)
        for m in self._pattern.finditer(norm):
            value = m.group(1)
            if not saudi_id_is_valid(value):
                continue
            is_iqama = value[0] == "2"
            yield Match(
                entity_type=EntityType.SAUDI_IQAMA if is_iqama else EntityType.SAUDI_NATIONAL_ID,
                category=Category.NATIONAL_IDENTIFIER,
                confidence=Confidence.HIGH,
                start=m.start(1), end=m.end(1), value=value, detector=self.name,
                notes="checksum-valid; not verified against any registry",
            )


class SaudiIbanDetector(Detector):
    name = "saudi_iban"
    _pattern = re.compile(r"(?<![A-Z0-9])SA\d{2}(?:\s?[A-Z0-9]){20}(?![A-Z0-9])", re.IGNORECASE)

    def detect(self, text: str) -> Iterable[Match]:
        for m in self._pattern.finditer(text):
            compact = re.sub(r"\s", "", m.group(0)).upper()
            if len(compact) != 24 or not iban_mod97_is_valid(compact):
                continue
            yield Match(
                entity_type=EntityType.SAUDI_IBAN, category=Category.FINANCIAL,
                confidence=Confidence.HIGH, start=m.start(), end=m.end(),
                value=compact, detector=self.name, notes="mod-97 valid",
            )


class SaudiMobileDetector(Detector):
    name = "saudi_mobile"
    _pattern = re.compile(r"(?<!\d)(?:(?:00|\+)?966|0)5\d{8}(?!\d)")

    def detect(self, text: str) -> Iterable[Match]:
        norm = _normalise_digits(text)
        for m in self._pattern.finditer(norm):
            yield Match(
                entity_type=EntityType.SAUDI_MOBILE, category=Category.CONTACT,
                confidence=Confidence.MEDIUM, start=m.start(), end=m.end(),
                value=m.group(0), detector=self.name,
                notes="format-only; no checksum exists for MSISDN",
            )


class SaudiCrDetector(Detector):
    name = "saudi_cr"
    _context = re.compile(r"(?:C\.?R\.?|commercial\s+registration|سجل\s*تجاري|س\.?ت\.?)", re.IGNORECASE)
    _number = re.compile(r"(?<!\d)(\d{10})(?!\d)")

    def detect(self, text: str) -> Iterable[Match]:
        norm = _normalise_digits(text)
        spans = [m.span() for m in self._context.finditer(norm)]
        if not spans:
            return
        for m in self._number.finditer(norm):
            near = any(abs(m.start() - ke) <= 40 or abs(ks - m.end()) <= 40 for ks, ke in spans)
            if not near:
                continue
            yield Match(
                entity_type=EntityType.SAUDI_CR, category=Category.ORGANISATION,
                confidence=Confidence.LOW, start=m.start(1), end=m.end(1),
                value=m.group(1), detector=self.name,
                notes="format+context only; no published checksum",
            )


class MedicalRecordNumberDetector(Detector):
    name = "medical_record_number"
    _pattern = re.compile(
        r"(?:MRN|medical\s+record(?:\s+(?:no|number))?\.?"
        r"|رقم\s*(?:ال)?(?:ملف|سجل)(?:\s*(?:ال)?طبي)?"
        r"|(?:ال)?سجل\s*(?:ال)?طبي)"
        r"\s*[:#\-]?\s*([A-Za-z0-9\-]{4,20})",
        re.IGNORECASE,
    )

    def detect(self, text: str) -> Iterable[Match]:
        for m in self._pattern.finditer(text):
            yield Match(
                entity_type=EntityType.MEDICAL_RECORD_NUMBER, category=Category.SENSITIVE_HEALTH,
                confidence=Confidence.LOW, start=m.start(1), end=m.end(1),
                value=m.group(1), detector=self.name,
                notes="context-only; MRN has no national format. Health data: PDPL/NDMO.",
            )


SAUDI_DETECTORS = [
    SaudiNationalIdDetector(), SaudiIbanDetector(), SaudiMobileDetector(),
    SaudiCrDetector(), MedicalRecordNumberDetector(),
]
