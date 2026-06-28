"""Homoglyph / lookalike-domain detection.

Three signals, in decreasing certainty:

1. Homograph impersonation: a domain whose confusable *skeleton* matches
   a watchlist domain but whose raw form differs -> someone built a
   look-alike of a domain you care about. HIGH.
2. Mixed-script label: a single label combines two scripts (e.g. Latin +
   Cyrillic, or Latin + Arabic). Strong spoofing signal on its own. HIGH
   when it collides with a watchlist skeleton, otherwise MEDIUM.
3. Typosquat: skeleton is within a small edit distance of a watchlist
   domain (insert/delete/substitute/transpose). MEDIUM.

Punycode (xn--) labels are decoded best-effort before analysis so the
Unicode form is what gets checked.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from .confusables import is_mixed_script, scripts_in, skeleton

# Domain / URL-ish token. Captures registrable-looking host strings,
# including Unicode letters and xn-- labels.
_DOMAIN_RE = re.compile(
    r"(?<![\w@.-])"
    r"((?:https?://)?(?:[^\s/@:]+\.)+[^\s/@:.]{2,})",
    re.UNICODE,
)


@dataclass(frozen=True)
class DomainFinding:
    domain: str          # the host as found (scheme stripped)
    reason: str          # impersonation | mixed_script | typosquat
    confidence: str      # high | medium
    target: str | None   # watchlist entry it imitates, if any
    detail: str
    start: int
    end: int


def _decode_idna(host: str) -> str:
    """Best-effort decode of xn-- (punycode) labels to Unicode."""
    parts = []
    for label in host.split("."):
        if label.lower().startswith("xn--"):
            try:
                parts.append(label[4:].encode("ascii").decode("punycode"))
                continue
            except Exception:
                pass
        parts.append(label)
    return ".".join(parts)


def _strip_scheme(token: str) -> str:
    return re.sub(r"^https?://", "", token, flags=re.IGNORECASE)


def damerau_levenshtein(a: str, b: str) -> int:
    """Optimal string alignment distance (with adjacent transpositions)."""
    la, lb = len(a), len(b)
    if not la:
        return lb
    if not lb:
        return la
    prev2: list[int] = []
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if (i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]):
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        prev2, prev = prev, cur
    return prev[lb]


def _registrable_skeleton(host: str) -> str:
    """Skeleton of the host without the public-suffix-ish tail, lowercased.

    We compare on the full host skeleton; the TLD is included because
    spoofs often swap the TLD too (example.com -> example.co).
    """
    return skeleton(_decode_idna(host))


def extract_domains(text: str) -> list[tuple[str, int, int]]:
    """Return (host, start, end) for domain-like tokens in text."""
    out = []
    for m in _DOMAIN_RE.finditer(text):
        token = m.group(1)
        host = _strip_scheme(token)
        # offset of host within the original match
        offset = m.start(1) + (len(token) - len(host))
        out.append((host, offset, offset + len(host)))
    return out


def analyze_domain(
    host: str,
    watchlist: Sequence[str] | None = None,
    *,
    typosquat_max_distance: int = 1,
    start: int = 0,
    end: int | None = None,
) -> list[DomainFinding]:
    """Analyse a single host. Returns zero or more findings."""
    end = end if end is not None else len(host)
    decoded = _decode_idna(host)
    findings: list[DomainFinding] = []

    wl = list(watchlist or [])
    wl_skeletons = {w: _registrable_skeleton(w) for w in wl}
    host_skel = _registrable_skeleton(host)

    # 1 + 3: compare against watchlist.
    for w, w_skel in wl_skeletons.items():
        if w.lower() == decoded.lower() or w.lower() == host.lower():
            continue  # exact legitimate match, not a spoof
        if host_skel == w_skel:
            findings.append(DomainFinding(
                domain=host, reason="impersonation", confidence="high",
                target=w, start=start, end=end,
                detail=f"confusable skeleton matches '{w}'",
            ))
        elif damerau_levenshtein(host_skel, w_skel) <= typosquat_max_distance:
            findings.append(DomainFinding(
                domain=host, reason="typosquat", confidence="medium",
                target=w, start=start, end=end,
                detail=f"within edit distance {typosquat_max_distance} of '{w}'",
            ))

    # 2: mixed-script labels (independent of watchlist).
    if not any(f.reason == "impersonation" for f in findings):
        for label in decoded.split("."):
            if is_mixed_script(label):
                scr = ", ".join(sorted(scripts_in(label)))
                findings.append(DomainFinding(
                    domain=host, reason="mixed_script",
                    confidence="medium", target=None, start=start, end=end,
                    detail=f"label '{label}' mixes scripts: {scr}",
                ))
                break

    return findings


def scan_text(
    text: str,
    watchlist: Sequence[str] | None = None,
    *,
    typosquat_max_distance: int = 1,
) -> list[DomainFinding]:
    """Extract domains from free text and analyse each."""
    results: list[DomainFinding] = []
    for host, s, e in extract_domains(text):
        results.extend(analyze_domain(
            host, watchlist,
            typosquat_max_distance=typosquat_max_distance, start=s, end=e,
        ))
    return results
