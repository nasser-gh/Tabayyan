"""Arabic personal-name detection (heuristic, context-gated).

NOT machine-learning NER. A precision-oriented heuristic: a name fires only
with supporting evidence —
  (a) a name-introducing trigger ("اسم المريض", "السيد", "د.") followed by
      Arabic tokens, or
  (b) strong name particles in the run ("عبدالله", "عبد العزيز", "بن",
      "بنت", "آل", "أبو").

Captured spans are trimmed of leading/trailing common words to fix name
boundaries. Confidence is LOW by design: recall is intentionally traded for
precision. Tagged PERSON — sensitive under PDPL/NDMO in a health context.
"""
from __future__ import annotations

import re
from typing import Iterable

from ..entities import Category, Confidence, EntityType, Match
from .base import Detector

# Arabic LETTERS only — excludes Arabic punctuation (comma U+060C,
# semicolon U+061B, question U+061F, etc.) which must break name tokens.
_AR = r"\u0621-\u063A\u0640-\u064A\u0671-\u06D3\u0750-\u077F\u08A0-\u08FF"
_AR_TOKEN = rf"[{_AR}]{{2,}}"

# Common non-name Arabic tokens that should not be inside a captured name.
_STOPWORDS = {
    "اليوم", "تمت", "تم", "في", "من", "إلى", "الى", "على", "عن", "قد", "كان",
    "هذا", "هذه", "الذي", "التي", "ثم", "حيث", "بعد", "قبل", "مع", "أو", "او",
    "قام", "راجع", "راجعنا", "وصل", "حضر", "غادر", "اليومين", "أمس", "غدا",
    "المستشفى", "العيادة", "القسم", "الموعد", "الملف", "السجل",
    "المريض", "المراجع", "الموظف", "السيد", "السيدة", "الدكتور",
    "الدكتورة", "الطبيب", "طبيب", "اسم",
    "الهوية", "الإقامة", "الاقامة", "الآيبان", "الايبان", "الجوال",
    "الرقم", "رقم", "الحساب", "العنوان", "التاريخ", "الجنسية",
}

_TRIGGER = re.compile(
    rf"(?:اسم\s*(?:المريض|المراجع|الموظف)?|المريض|المراجع|السيد(?:ة)?|"
    rf"الدكتور(?:ة)?|د\.\s*|طبيب|الطبيب|patient\s+name|name)\s*[:：\-]?\s*"
    rf"((?:{_AR_TOKEN}\s+){{0,3}}{_AR_TOKEN})",
)

_PARTICLE_RUN = re.compile(
    rf"((?:{_AR_TOKEN}\s+)?"
    rf"(?:عبد\s*[{_AR}]+|بن|بنت|آل|أبو|أم|ابن)"
    rf"(?:\s+{_AR_TOKEN}){{1,3}})",
)

_TOKEN_SPAN = re.compile(rf"[{_AR}]+")


def _trim_to_name(text: str, start: int, end: int) -> tuple[int, int] | None:
    """Trim leading/trailing stopword tokens; return tightened span or None."""
    toks = [(m.start(), m.end()) for m in _TOKEN_SPAN.finditer(text, start, end)]
    while toks and text[toks[-1][0]:toks[-1][1]] in _STOPWORDS:
        toks.pop()
    while toks and text[toks[0][0]:toks[0][1]] in _STOPWORDS:
        toks.pop(0)
    if not toks:
        return None
    return toks[0][0], toks[-1][1]


class ArabicNameDetector(Detector):
    name = "arabic_name"

    def detect(self, text: str) -> Iterable[Match]:
        seen: list[tuple[int, int]] = []

        def add(raw_start, raw_end):
            span = _trim_to_name(text, raw_start, raw_end)
            if span is None:
                return None
            s, e = span
            if any(os <= s < oe for os, oe in seen):
                return None
            seen.append((s, e))
            return Match(
                entity_type=EntityType.ARABIC_NAME, category=Category.PERSON,
                confidence=Confidence.LOW, start=s, end=e, value=text[s:e],
                detector=self.name,
                notes="heuristic, context-gated; not ML NER. PERSON data under PDPL/NDMO.",
            )

        for m in _TRIGGER.finditer(text):
            r = add(m.start(1), m.end(1))
            if r:
                yield r
        for m in _PARTICLE_RUN.finditer(text):
            r = add(m.start(1), m.end(1))
            if r:
                yield r
