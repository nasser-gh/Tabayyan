"""Offset-preserving input normalization (anti-evasion pre-pass).

Detectors are easy to dodge with characters that *look* normal but break a
regex: a zero-width space wedged between two ID digits, Arabic-Indic or
fullwidth digits, a bidi control inside an IBAN. This module folds those
away **once, centrally**, so every detector benefits — not just the Saudi
ones that already strip Arabic-Indic digits.

The catch is offsets: detection runs on the normalized string, but redaction
must rewrite the *original* text. `normalize()` therefore returns a mapping
from every normalized character back to the original index it came from, so a
match found on the clean text can be projected onto the exact original span
(invisible characters in the middle included).

Transforms (each is offset-trackable):
  * delete Unicode format/bidi characters (category Cf) + soft hyphen — the
    zero-width and direction-control family used to split tokens;
  * fold Arabic-Indic (٠-٩), Eastern/Persian (۰-۹) and fullwidth digits to
    ASCII;
  * apply per-character NFKC for the remaining compatibility forms (fullwidth
    Latin, Arabic presentation forms, ligatures, …).

NFKC is applied per character on purpose: it never composes across original
characters, which keeps the back-mapping exact (one original index per
emitted character) at the cost of not merging base+combining pairs — not an
evasion vector for the identifiers we detect.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass

# Arabic-Indic + Eastern-Arabic/Persian digits -> ASCII. (NFKC already folds
# fullwidth digits, but these it leaves untouched.)
_DIGIT_FOLD = {
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
    "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
    "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
}

# Extra invisibles to strip that are not category Cf on every platform.
_EXTRA_STRIP = {"­", "᠎"}  # SOFT HYPHEN, MONGOLIAN VOWEL SEPARATOR


def _is_stripped(ch: str) -> bool:
    return ch in _EXTRA_STRIP or unicodedata.category(ch) == "Cf"


@dataclass(frozen=True)
class Normalized:
    """Normalized text plus a back-map to the original offsets."""

    text: str
    original: str
    _src: tuple[int, ...]  # _src[k] = original index of normalized char k

    def map_span(self, start: int, end: int) -> tuple[int, int]:
        """Project a [start, end) span on the normalized text back onto the
        original text. The original span covers every source character the
        normalized run came from, including any deleted invisibles between."""
        n = len(self._src)
        if start >= end:  # empty match — collapse to a single original point
            pos = self._src[start] if 0 <= start < n else len(self.original)
            return pos, pos
        o_start = self._src[start]
        o_end = self._src[end - 1] + 1
        return o_start, o_end


def normalize(text: str) -> Normalized:
    out: list[str] = []
    src: list[int] = []
    for i, ch in enumerate(text):
        if _is_stripped(ch):
            continue
        folded = _DIGIT_FOLD.get(ch)
        if folded is None:
            folded = unicodedata.normalize("NFKC", ch)
            if not folded:  # e.g. a lone combining mark NFKC drops
                continue
        for c in folded:
            out.append(c)
            src.append(i)
    return Normalized(text="".join(out), original=text, _src=tuple(src))
