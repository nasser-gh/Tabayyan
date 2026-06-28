"""Configuration: customise detection without editing code.

Load a JSON config to enable/disable detectors, add custom regex
detectors, extend the confusable map, and tune thresholds. JSON is used
(not TOML) to keep zero runtime dependencies on Python 3.9.

Schema (all keys optional):
{
  "disable": ["saudi_cr", "arabic_name"],
  "typosquat_max_distance": 2,
  "confusables": {"ⅴ": "v"},
  "custom_detectors": [
    {"label": "employee_id", "pattern": "EMP-\\\\d{6}",
     "category": "organisation", "confidence": "medium"}
  ]
}

Custom-detector matches use entity_type CUSTOM; their configured label is
preserved in the `detector` and `notes` fields and in the mask placeholder.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .confusables import register_confusables
from .detectors import DEFAULT_DETECTORS, Detector
from .engine import DetectionEngine
from .entities import Category, Confidence, EntityType, Match

_CONF = {c.value: c for c in Confidence}
_CAT = {c.value: c for c in Category}


class CustomRegexDetector(Detector):
    """A user-defined regex detector loaded from config."""

    def __init__(self, label: str, pattern: str, category: Category,
                 confidence: Confidence) -> None:
        self.name = f"custom:{label}"
        self.label = label
        self._rx = re.compile(pattern)
        self._category = category
        self._confidence = confidence

    def detect(self, text: str) -> Iterable[Match]:
        for m in self._rx.finditer(text):
            yield Match(
                entity_type=EntityType.CUSTOM, category=self._category,
                confidence=self._confidence, start=m.start(), end=m.end(),
                value=m.group(0), detector=self.name, label=self.label,
                notes=f"custom detector '{self.label}'",
            )

    def mask_label(self) -> str:
        return f"[{self.label.upper()}]"


@dataclass
class Config:
    disable: set[str] = field(default_factory=set)
    typosquat_max_distance: int = 1
    custom_detectors: list[CustomRegexDetector] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        for ch, sk in (data.get("confusables") or {}).items():
            register_confusables({ch: sk})
        customs = []
        for spec in data.get("custom_detectors", []):
            customs.append(CustomRegexDetector(
                label=spec["label"], pattern=spec["pattern"],
                category=_CAT[spec.get("category", "organisation")],
                confidence=_CONF[spec.get("confidence", "medium")],
            ))
        return cls(
            disable=set(data.get("disable", [])),
            typosquat_max_distance=int(data.get("typosquat_max_distance", 1)),
            custom_detectors=customs,
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "Config":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def build_engine(self) -> DetectionEngine:
        detectors = [d for d in DEFAULT_DETECTORS if d.name not in self.disable]
        detectors.extend(self.custom_detectors)
        return DetectionEngine(detectors)
