"""Opt-in lookalike/homoglyph domain detector.

Not part of DEFAULT_DETECTORS: it needs a watchlist to be most useful and
it emits THREAT findings, not PII. Construct it explicitly (optionally
with a watchlist) and pass it to DetectionEngine, or use the `domains`
CLI command.
"""
from __future__ import annotations

from typing import Iterable, Sequence

from ..entities import Category, Confidence, EntityType, Match
from ..homoglyph import scan_text
from .base import Detector

_CONF = {"high": Confidence.HIGH, "medium": Confidence.MEDIUM, "low": Confidence.LOW}


class LookalikeDomainDetector(Detector):
    name = "lookalike_domain"

    def __init__(self, watchlist: Sequence[str] | None = None,
                 typosquat_max_distance: int = 1) -> None:
        self.watchlist = list(watchlist or [])
        self.typosquat_max_distance = typosquat_max_distance

    def detect(self, text: str) -> Iterable[Match]:
        for f in scan_text(text, self.watchlist,
                           typosquat_max_distance=self.typosquat_max_distance):
            note = f.detail if f.target is None else f"{f.reason}: {f.detail}"
            yield Match(
                entity_type=EntityType.SUSPICIOUS_DOMAIN,
                category=Category.THREAT,
                confidence=_CONF[f.confidence],
                start=f.start, end=f.end, value=f.domain,
                detector=self.name, notes=note,
            )
