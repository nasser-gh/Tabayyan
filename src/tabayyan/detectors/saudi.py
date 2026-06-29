"""Saudi-specific entity detectors — the differentiator."""
from __future__ import annotations

import re
from typing import Iterable

from ..checksums import iban_mod97_is_valid, saudi_id_is_valid
from ..entities import Category, Confidence, EntityType, Match
from .base import Detector

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

# Context window (chars) within which a label must sit for a context-gated,
# format-only identifier to be accepted. Mirrors the original CR heuristic.
_CONTEXT_WINDOW = 40


def _normalise_digits(text: str) -> str:
    return text.translate(_ARABIC_DIGITS)


def _near(start: int, end: int, spans: list[tuple[int, int]], window: int = _CONTEXT_WINDOW) -> bool:
    """True if [start, end) is within `window` chars of any context span."""
    return any(abs(start - ke) <= window or abs(ks - end) <= window for ks, ke in spans)


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
            if not _near(m.start(), m.end(), spans):
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


class SaudiLandlineDetector(Detector):
    """Fixed-line numbers: +966 1X XXXXXXX or 0 1X XXXXXXX (area codes 11-17).

    Distinct prefix from mobile (5...), so it is reliable standalone.
    """
    name = "saudi_landline"
    _pattern = re.compile(r"(?<!\d)(?:(?:00|\+)?966|0)1[1-7]\d{7}(?!\d)")

    def detect(self, text: str) -> Iterable[Match]:
        norm = _normalise_digits(text)
        for m in self._pattern.finditer(norm):
            yield Match(
                entity_type=EntityType.SAUDI_LANDLINE, category=Category.CONTACT,
                confidence=Confidence.MEDIUM, start=m.start(), end=m.end(),
                value=m.group(0), detector=self.name,
                notes="format-only; no checksum exists for a landline number",
            )


class SaudiVatDetector(Detector):
    """ZATCA VAT / tax registration number: 15 digits, context-gated.

    A bare 15-digit run also matches some card PANs (e.g. Amex), so this is
    gated on a tax-context label and emitted at MEDIUM; if a span also looks
    like a Luhn-valid card, the engine keeps the higher-confidence card match.
    """
    name = "saudi_vat"
    _context = re.compile(
        r"(?:VAT|TRN|tax\s+(?:id|number|registration)|الرقم\s*الضريبي|ضريب)",
        re.IGNORECASE,
    )
    _number = re.compile(r"(?<!\d)(\d{15})(?!\d)")

    def detect(self, text: str) -> Iterable[Match]:
        norm = _normalise_digits(text)
        spans = [m.span() for m in self._context.finditer(norm)]
        if not spans:
            return
        for m in self._number.finditer(norm):
            if not _near(m.start(1), m.end(1), spans):
                continue
            yield Match(
                entity_type=EntityType.SAUDI_VAT, category=Category.FINANCIAL,
                confidence=Confidence.MEDIUM, start=m.start(1), end=m.end(1),
                value=m.group(1), detector=self.name,
                notes="format+context only; ZATCA TRN has no public checksum",
            )


class SaudiPassportDetector(Detector):
    """Saudi passport number: one letter + 8 digits. Context-gated (LOW)."""
    name = "saudi_passport"
    _context = re.compile(r"(?:passport|جواز(?:\s*سفر)?|رقم\s*الجواز)", re.IGNORECASE)
    _number = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]\d{8})(?![A-Za-z0-9])")

    def detect(self, text: str) -> Iterable[Match]:
        spans = [m.span() for m in self._context.finditer(text)]
        if not spans:
            return
        for m in self._number.finditer(text):
            if not _near(m.start(1), m.end(1), spans):
                continue
            yield Match(
                entity_type=EntityType.SAUDI_PASSPORT, category=Category.NATIONAL_IDENTIFIER,
                confidence=Confidence.LOW, start=m.start(1), end=m.end(1),
                value=m.group(1), detector=self.name,
                notes="format+context only; passport numbers have no public checksum",
            )


class SaudiBorderNumberDetector(Detector):
    """Border/visa number (رقم الحدود / رقم التأشيرة): 10 digits, context-gated."""
    name = "saudi_border_number"
    _context = re.compile(
        r"(?:border\s*(?:no|number)|رقم\s*الحدود|تأشير|visa\s*(?:no|number))",
        re.IGNORECASE,
    )
    _number = re.compile(r"(?<!\d)(\d{10})(?!\d)")

    def detect(self, text: str) -> Iterable[Match]:
        norm = _normalise_digits(text)
        spans = [m.span() for m in self._context.finditer(norm)]
        if not spans:
            return
        for m in self._number.finditer(norm):
            if not _near(m.start(1), m.end(1), spans):
                continue
            yield Match(
                entity_type=EntityType.SAUDI_BORDER_NUMBER, category=Category.NATIONAL_IDENTIFIER,
                confidence=Confidence.LOW, start=m.start(1), end=m.end(1),
                value=m.group(1), detector=self.name,
                notes="format+context only; issued to visitors (Hajj/Umrah/visa)",
            )


class SaudiNationalAddressDetector(Detector):
    """National Address short code (e.g. RRRD2929): 4 letters + 4 digits, context-gated."""
    name = "saudi_national_address"
    _context = re.compile(
        r"(?:national\s*address|short\s*address|العنوان\s*الوطني|الرمز\s*البريدي|رمز\s*المبنى)",
        re.IGNORECASE,
    )
    _code = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]{4}\d{4})(?![A-Za-z0-9])")

    def detect(self, text: str) -> Iterable[Match]:
        spans = [m.span() for m in self._context.finditer(text)]
        if not spans:
            return
        for m in self._code.finditer(text):
            if not _near(m.start(1), m.end(1), spans):
                continue
            yield Match(
                entity_type=EntityType.SAUDI_NATIONAL_ADDRESS, category=Category.CONTACT,
                confidence=Confidence.LOW, start=m.start(1), end=m.end(1),
                value=m.group(1), detector=self.name,
                notes="format+context only; Saudi Post short address",
            )


class SaudiUnifiedNumberDetector(Detector):
    """Unified national number for establishments (700 number): starts with 7,
    10 digits. Context-gated (LOW)."""
    name = "saudi_unified_number"
    # \b700\b matches the colloquial "700 number" but NOT a "700" that is just
    # a digit run inside the candidate itself (which would self-trigger).
    _context = re.compile(r"(?:unified\s*(?:national\s*)?number|الرقم\s*الموحد|\b700\b)", re.IGNORECASE)
    _number = re.compile(r"(?<!\d)(7\d{9})(?!\d)")

    def detect(self, text: str) -> Iterable[Match]:
        norm = _normalise_digits(text)
        spans = [m.span() for m in self._context.finditer(norm)]
        if not spans:
            return
        for m in self._number.finditer(norm):
            if not _near(m.start(1), m.end(1), spans):
                continue
            yield Match(
                entity_type=EntityType.SAUDI_UNIFIED_NUMBER, category=Category.ORGANISATION,
                confidence=Confidence.LOW, start=m.start(1), end=m.end(1),
                value=m.group(1), detector=self.name,
                notes="format+context only; establishment unified number",
            )


SAUDI_DETECTORS = [
    SaudiNationalIdDetector(), SaudiIbanDetector(), SaudiMobileDetector(),
    SaudiLandlineDetector(), SaudiCrDetector(), SaudiVatDetector(),
    SaudiPassportDetector(), SaudiBorderNumberDetector(),
    SaudiNationalAddressDetector(), SaudiUnifiedNumberDetector(),
    MedicalRecordNumberDetector(),
]
