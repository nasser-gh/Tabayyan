"""Shared fuzz invariants.

One place defines what "correct" means for an arbitrary input, used by both the
Atheris target (`fuzz_pipeline.py`) and the replay tool (`replay.py`) so a crash
found by the fuzzer reproduces identically offline. No timing assertions —
runtime is an observation for the workflow, not a correctness signal.
"""
from __future__ import annotations

from tabayyan import DetectionEngine, RedactionMode, redact, restore, scan_and_redact
from tabayyan.normalize import normalize

_engine = DetectionEngine()


def check_text(text: str) -> None:
    """Assert every pipeline invariant for `text`. Raises AssertionError on a
    violation (that is what the fuzzer reports as a crash)."""
    # --- normalization ---
    n = normalize(text)
    assert normalize(n.text).text == n.text, "normalize is not idempotent"
    assert len(n._src) == len(n.text), "offset map length mismatch"
    for k in range(len(n.text)):
        start, end = n.map_span(k, k + 1)
        assert 0 <= start <= end <= len(text), "normalized offset out of bounds"

    # --- detection ---
    matches = _engine.scan(text)
    for m in matches:
        assert 0 <= m.start <= m.end <= len(text), "match span out of bounds"
        assert isinstance(m.value, str)

    # --- redaction does not crash and returns text ---
    assert isinstance(redact(text, matches, RedactionMode.MASK).text, str)

    # --- tokenize round-trip is lossless when the input can't collide with a
    # placeholder like <SAUDI_NATIONAL_ID_1> (a documented limitation) ---
    if "<" not in text and ">" not in text:
        r = scan_and_redact(text, RedactionMode.TOKENIZE)
        assert restore(r.text, r.vault) == text, "tokenize/restore is not lossless"


def run_bytes(data: bytes) -> str:
    """Decode bytes the way the CLI does, then check invariants. Returns the
    decoded text for inspection."""
    text = data.decode("utf-8", errors="replace")
    check_text(text)
    return text
