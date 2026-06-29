"""Microsoft Presidio integration (optional extra: `tabayyan[presidio]`).

Exposes Tabayyan's *validated* Saudi/Arabic detectors as Presidio
recognizers, so existing Presidio users gain Saudi coverage with one
import. It deliberately complements Presidio — it adds the entities
Presidio lacks (Saudi National ID/Iqama/IBAN/CR/mobile, MRN, Arabic names,
lookalike domains) and does NOT duplicate Presidio's email/credit-card/IP
recognizers.

Parity: each recognizer wraps the same DetectionEngine used standalone, so
detections (and checksum validation) are identical to the core library.
The only translation is Tabayyan confidence -> Presidio score and
Tabayyan entity type -> Presidio entity name.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

try:
    from presidio_analyzer import EntityRecognizer, RecognizerResult
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "The Presidio integration requires presidio-analyzer. "
        "Install it with:  pip install 'tabayyan[presidio]'"
    ) from exc

from ..detectors import SAUDI_DETECTORS, ArabicNameDetector
from ..detectors.domains import LookalikeDomainDetector
from ..engine import DetectionEngine
from ..entities import Confidence, EntityType

# Tabayyan confidence -> Presidio score.
SCORE = {Confidence.HIGH: 0.95, Confidence.MEDIUM: 0.6, Confidence.LOW: 0.4}

# Tabayyan entity type -> Presidio entity name.
ENTITY_MAP = {
    EntityType.SAUDI_NATIONAL_ID: "SA_NATIONAL_ID",
    EntityType.SAUDI_IQAMA: "SA_IQAMA",
    EntityType.SAUDI_IBAN: "SA_IBAN",
    EntityType.SAUDI_CR: "SA_CR",
    EntityType.SAUDI_MOBILE: "SA_PHONE_NUMBER",
    EntityType.SAUDI_LANDLINE: "SA_PHONE_NUMBER",
    EntityType.SAUDI_VAT: "SA_VAT",
    EntityType.SAUDI_PASSPORT: "SA_PASSPORT",
    EntityType.SAUDI_BORDER_NUMBER: "SA_BORDER_NUMBER",
    EntityType.SAUDI_NATIONAL_ADDRESS: "SA_NATIONAL_ADDRESS",
    EntityType.SAUDI_UNIFIED_NUMBER: "SA_UNIFIED_NUMBER",
    EntityType.MEDICAL_RECORD_NUMBER: "MEDICAL_RECORD_NUMBER",
    EntityType.ARABIC_NAME: "PERSON",
    EntityType.SUSPICIOUS_DOMAIN: "SUSPICIOUS_DOMAIN",
}


class _BaseTabayyanRecognizer(EntityRecognizer):
    """Wrap a DetectionEngine as a Presidio EntityRecognizer."""

    def __init__(self, engine: DetectionEngine, name: str, language: str = "en") -> None:
        self._engine = engine
        supported = sorted({ENTITY_MAP[t] for t in self._produced_types()})
        super().__init__(supported_entities=supported, name=name,
                         supported_language=language)

    def _produced_types(self) -> set:
        types = set()
        for det in self._engine.detectors:
            types |= _DETECTOR_TYPES.get(type(det).__name__, set())
        return {t for t in types if t in ENTITY_MAP}

    def load(self) -> None:  # no model to load
        return None

    def analyze(self, text: str, entities: List[str],
                nlp_artifacts=None) -> List[RecognizerResult]:
        results: List[RecognizerResult] = []
        for m in self._engine.scan(text):
            mapped = ENTITY_MAP.get(m.entity_type)
            if mapped is None or (entities and mapped not in entities):
                continue
            results.append(RecognizerResult(
                entity_type=mapped, start=m.start, end=m.end,
                score=SCORE[m.confidence],
                recognition_metadata={
                    RecognizerResult.RECOGNIZER_NAME_KEY: self.name,
                    "tabayyan_confidence": m.confidence.value,
                    "tabayyan_category": m.category.value,
                    "tabayyan_notes": m.notes,
                },
            ))
        return results


# Which EntityTypes each detector class can emit (for supported_entities).
_DETECTOR_TYPES = {
    "SaudiNationalIdDetector": {EntityType.SAUDI_NATIONAL_ID, EntityType.SAUDI_IQAMA},
    "SaudiIbanDetector": {EntityType.SAUDI_IBAN},
    "SaudiMobileDetector": {EntityType.SAUDI_MOBILE},
    "SaudiLandlineDetector": {EntityType.SAUDI_LANDLINE},
    "SaudiCrDetector": {EntityType.SAUDI_CR},
    "SaudiVatDetector": {EntityType.SAUDI_VAT},
    "SaudiPassportDetector": {EntityType.SAUDI_PASSPORT},
    "SaudiBorderNumberDetector": {EntityType.SAUDI_BORDER_NUMBER},
    "SaudiNationalAddressDetector": {EntityType.SAUDI_NATIONAL_ADDRESS},
    "SaudiUnifiedNumberDetector": {EntityType.SAUDI_UNIFIED_NUMBER},
    "MedicalRecordNumberDetector": {EntityType.MEDICAL_RECORD_NUMBER},
    "ArabicNameDetector": {EntityType.ARABIC_NAME},
    "LookalikeDomainDetector": {EntityType.SUSPICIOUS_DOMAIN},
}


class SaudiRecognizer(_BaseTabayyanRecognizer):
    """All Saudi/Arabic PII detectors (National ID, Iqama, IBAN, CR, mobile,
    MRN, Arabic names) as one Presidio recognizer."""

    def __init__(self, language: str = "en") -> None:
        engine = DetectionEngine([*SAUDI_DETECTORS, ArabicNameDetector()])
        super().__init__(engine, name="TabayyanSaudiRecognizer", language=language)


class LookalikeDomainRecognizer(_BaseTabayyanRecognizer):
    """Homoglyph / lookalike-domain detection as a Presidio recognizer."""

    def __init__(self, watchlist: Optional[Sequence[str]] = None,
                 language: str = "en") -> None:
        engine = DetectionEngine([LookalikeDomainDetector(watchlist=watchlist)])
        super().__init__(engine, name="TabayyanLookalikeDomainRecognizer",
                         language=language)


def get_saudi_recognizers(language: str = "en",
                          watchlist: Optional[Sequence[str]] = None
                          ) -> List[EntityRecognizer]:
    """Return Tabayyan recognizers ready to add to a Presidio registry."""
    recs: List[EntityRecognizer] = [SaudiRecognizer(language=language)]
    if watchlist:
        recs.append(LookalikeDomainRecognizer(watchlist=watchlist, language=language))
    return recs


def register_saudi_recognizers(target, language: str = "en",
                               watchlist: Optional[Sequence[str]] = None) -> None:
    """Add Tabayyan recognizers to a RecognizerRegistry or an AnalyzerEngine."""
    registry = getattr(target, "registry", target)
    for rec in get_saudi_recognizers(language=language, watchlist=watchlist):
        registry.add_recognizer(rec)
