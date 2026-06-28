"""Streaming scan for large files.

Reads a file in chunks with an overlap window so an entity straddling a
chunk boundary is still detected exactly once. Yields Match objects with
file-global character offsets.

Correctness: each chunk covers [pos, pos+chunk+overlap). A match is kept
only if it STARTS within the non-overlap region [pos, pos+chunk) — except
for the final chunk, which keeps everything. The overlap must exceed the
longest detectable entity; the default (512) comfortably covers IBANs,
IDs, and multi-token names.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

from .engine import DetectionEngine
from .entities import Match

DEFAULT_CHUNK = 1 << 20   # 1 MiB
DEFAULT_OVERLAP = 512


def scan_file(
    path: str | Path,
    engine: DetectionEngine | None = None,
    *,
    chunk_size: int = DEFAULT_CHUNK,
    overlap: int = DEFAULT_OVERLAP,
    encoding: str = "utf-8",
) -> Iterator[Match]:
    """Yield Matches with file-global offsets, scanning incrementally."""
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    engine = engine or DetectionEngine()
    path = Path(path)

    with path.open("r", encoding=encoding, errors="replace") as fh:
        buffer = ""
        base = 0          # global offset of buffer[0]
        emitted: set[tuple[int, int, str]] = set()
        while True:
            piece = fh.read(chunk_size)
            last = piece == ""
            buffer += piece
            if not buffer:
                break

            # Region whose matches we trust this round.
            keep_until = len(buffer) if last else max(0, len(buffer) - overlap)

            for m in engine.scan(buffer):
                if m.start >= keep_until and not last:
                    continue
                key = (base + m.start, base + m.end, m.entity_type.value)
                if key in emitted:
                    continue
                emitted.add(key)
                yield Match(
                    entity_type=m.entity_type, category=m.category,
                    confidence=m.confidence, start=base + m.start,
                    end=base + m.end, value=m.value, detector=m.detector,
                    notes=m.notes,
                )

            if last:
                break
            # Slide: drop the trusted prefix, retain the overlap tail.
            drop = keep_until
            base += drop
            buffer = buffer[drop:]
