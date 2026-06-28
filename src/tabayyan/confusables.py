"""Script classification and confusable-skeleton folding.

Used by the homoglyph subsystem to catch domains that impersonate a
target using visually-confusable characters (IDN homograph attacks) or
mix scripts. The confusables map is a curated, practical subset of the
Unicode confusables data — extensible, not exhaustive. See
homoglyph.py for the detection logic that consumes these primitives.
"""
from __future__ import annotations

# Curated confusable -> ASCII/canonical skeleton map.
# Focus: characters realistically used to spoof Latin domains
# (Cyrillic, Greek, fullwidth, digit/letter swaps) plus Arabic-Indic
# digits which appear in mixed Arabic/Latin spoofs.
_CONFUSABLES: dict[str, str] = {
    # Cyrillic -> Latin
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x",
    "у": "y", "к": "k", "м": "m", "н": "h", "т": "t", "в": "b",
    "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "ɡ": "g",
    "ӏ": "l", "Ӏ": "l", "ⅼ": "l", "ｊ": "j",
    # Greek -> Latin
    "α": "a", "ο": "o", "ν": "v", "ρ": "p", "τ": "t", "υ": "u",
    "ι": "i", "κ": "k", "χ": "x", "ε": "e",
    # Fullwidth Latin -> ASCII
    "ａ": "a", "ｂ": "b", "ｃ": "c", "ｄ": "d", "ｅ": "e", "ｏ": "o",
    "ｐ": "p", "ｓ": "s", "ｘ": "x", "ｉ": "i", "ｌ": "l", "ｍ": "m",
    "ｎ": "n", "ｇ": "g", "ｔ": "t", "ｒ": "r", "ｕ": "u",
    # Digit/letter confusions folded to a single skeleton
    "0": "o", "1": "l", "5": "s", "8": "b",
    "l": "l", "I": "l", "|": "l",
    # Arabic-Indic and Eastern-Arabic digits -> ASCII digits then folded
    "٠": "o", "١": "l", "٢": "2", "٣": "3", "٤": "4", "٥": "s",
    "٦": "6", "٧": "7", "٨": "b", "٩": "9",
    "۰": "o", "۱": "l", "۲": "2", "۳": "3", "۴": "4", "۵": "s",
    "۶": "6", "۷": "7", "۸": "b", "۹": "9",
}


def register_confusables(extra: dict[str, str]) -> None:
    """Merge user-supplied confusable mappings into the global map."""
    _CONFUSABLES.update(extra)


def skeleton(label: str) -> str:
    """Fold a string to its confusable skeleton (lowercased).

    Two strings with the same skeleton look alike. This is the core
    primitive for homograph-impersonation detection.
    """
    out = []
    for ch in label.lower():
        out.append(_CONFUSABLES.get(ch, ch))
    return "".join(out)


# Script ranges (start, end, name). Order matters only for first-match.
_SCRIPT_RANGES = [
    (0x0041, 0x005A, "Latin"), (0x0061, 0x007A, "Latin"),
    (0x00C0, 0x024F, "Latin"),
    (0x0370, 0x03FF, "Greek"), (0x1F00, 0x1FFF, "Greek"),
    (0x0400, 0x04FF, "Cyrillic"), (0x0500, 0x052F, "Cyrillic"),
    (0x0600, 0x06FF, "Arabic"), (0x0750, 0x077F, "Arabic"),
    (0x08A0, 0x08FF, "Arabic"), (0xFB50, 0xFDFF, "Arabic"),
    (0xFE70, 0xFEFF, "Arabic"),
    (0x0590, 0x05FF, "Hebrew"),
    (0x4E00, 0x9FFF, "Han"),
    (0x3040, 0x30FF, "Kana"),
]


def script_of(ch: str) -> str:
    """Return a coarse script name for a single character.

    Digits and ASCII punctuation are 'Common' (script-neutral) so they
    don't trigger false mixed-script alarms on their own.
    """
    cp = ord(ch)
    if ch.isdigit() and cp < 0x0660:
        return "Common"
    if ch in "-._/:":
        return "Common"
    for start, end, name in _SCRIPT_RANGES:
        if start <= cp <= end:
            return name
    return "Common"


def scripts_in(label: str) -> set[str]:
    """Return the set of non-Common scripts present in a label."""
    return {s for s in (script_of(c) for c in label) if s != "Common"}


def is_mixed_script(label: str) -> bool:
    """True if a single label mixes two or more distinct scripts.

    Mixing scripts inside one domain label is a strong spoofing signal:
    legitimate labels almost never combine, e.g., Latin and Cyrillic.
    """
    return len(scripts_in(label)) >= 2
