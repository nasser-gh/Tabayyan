"""Detection engine: normalizes, runs detectors, resolves overlaps. Offline, deterministic.

Input is first run through an offset-preserving normalization pass
(see normalize.py) so evasion via zero-width/bidi characters or
Arabic-Indic/fullwidth digits is folded away before detection; matches are
projected back onto original offsets. Pure-ASCII input is left unchanged, so
the pass is transparent for the common case.

Overlap resolution: matches are ranked (confidence desc, then length desc,
then position), and each is accepted only if it does not overlap an
already-kept interval. Kept intervals are disjoint and held sorted by start,
so each overlap *check* is two bisect lookups rather than a linear scan.

Complexity: the initial sort is O(n log n); maintaining the sorted kept-set
uses list.insert, which is O(n) per accept, so the worst case is O(n²) for
pathologically dense inputs. In practice n (matches per prompt) is small and
the bisect checks dominate. A SortedList would make it true O(n log n) but
pulls in a dependency we keep out of the detection core.
"""
from __future__ import annotations

import bisect
from dataclasses import replace
from typing import Iterable, Sequence

from .detectors import Detector, default_detectors
from .entities import Confidence, Match
from .normalize import normalize

_CONFIDENCE_RANK = {Confidence.HIGH: 3, Confidence.MEDIUM: 2, Confidence.LOW: 1}


class DetectionEngine:
    def __init__(self, detectors: Sequence[Detector] | None = None, *, normalize_input: bool = True) -> None:
        self.detectors = list(detectors) if detectors is not None else default_detectors()
        self.normalize_input = normalize_input

    def scan(self, text: str) -> list[Match]:
        # Anti-evasion pre-pass: detectors run on normalized text, then each
        # match is projected back onto the original offsets so redaction
        # rewrites the real span (invisibles included). See normalize.py.
        if self.normalize_input:
            norm = normalize(text)
            scan_text = norm.text
        else:
            norm = None
            scan_text = text
        raw: list[Match] = []
        for det in self.detectors:
            for m in det.detect(scan_text):
                if norm is not None:
                    o_start, o_end = norm.map_span(m.start, m.end)
                    m = replace(m, start=o_start, end=o_end)
                raw.append(m)
        return self._resolve(raw)

    def _resolve(self, matches: Iterable[Match]) -> list[Match]:
        ordered = sorted(
            matches,
            key=lambda m: (-_CONFIDENCE_RANK[m.confidence], -(m.end - m.start), m.start),
        )
        kept_starts: list[int] = []   # sorted starts of kept (disjoint) intervals
        kept_ends: list[int] = []     # parallel ends
        result: list[Match] = []
        for m in ordered:
            i = bisect.bisect_right(kept_starts, m.start)
            # interval starting at/just-before m.start overlaps if its end > m.start
            if i > 0 and kept_ends[i - 1] > m.start:
                continue
            # next interval (starting after m.start) overlaps if it begins before m.end
            if i < len(kept_starts) and kept_starts[i] < m.end:
                continue
            kept_starts.insert(i, m.start)
            kept_ends.insert(i, m.end)
            result.append(m)
        result.sort(key=lambda m: m.start)
        return result
