"""Detection engine: runs detectors and resolves overlaps. Offline, deterministic.

Overlap resolution is O(n log n): matches are ranked (confidence desc, then
length desc, then position), and each is accepted only if it does not
overlap an already-kept interval. Kept intervals are disjoint and held
sorted by start, so an overlap check is two bisect lookups, not a linear
scan — critical on dense inputs.
"""
from __future__ import annotations

import bisect
from typing import Iterable, Sequence

from .detectors import DEFAULT_DETECTORS, Detector
from .entities import Confidence, Match

_CONFIDENCE_RANK = {Confidence.HIGH: 3, Confidence.MEDIUM: 2, Confidence.LOW: 1}


class DetectionEngine:
    def __init__(self, detectors: Sequence[Detector] | None = None) -> None:
        self.detectors = list(detectors) if detectors is not None else list(DEFAULT_DETECTORS)

    def scan(self, text: str) -> list[Match]:
        raw: list[Match] = []
        for det in self.detectors:
            raw.extend(det.detect(text))
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
