"""Tabayyan (تبيّن) — Saudi-aware PII detection & redaction for LLM pipelines.

Local-first. Zero telemetry. No network calls in the detection core.
"""
from __future__ import annotations

from .engine import DetectionEngine
from .entities import Category, Confidence, EntityType, Match
from .middleware import AuditLog, AuditRecord, Guard, ProtectResult, is_in_kingdom
from .providers import ProviderAdapter, register_adapter, resolve_adapter
from .redaction import RedactionItem, RedactionMode, RedactionResult, redact, restore

__version__ = "0.5.1"
__all__ = [
    "DetectionEngine",
    "Match",
    "EntityType",
    "Category",
    "Confidence",
    "RedactionMode",
    "RedactionResult",
    "RedactionItem",
    "redact",
    "restore",
    "Guard",
    "AuditLog",
    "AuditRecord",
    "ProtectResult",
    "is_in_kingdom",
    "ProviderAdapter",
    "register_adapter",
    "resolve_adapter",
    "scan",
    "scan_and_redact",
    "__version__",
]


def scan(text: str) -> list[Match]:
    """Convenience one-shot detection using the default detector set."""
    return DetectionEngine().scan(text)


def scan_and_redact(
    text: str,
    mode: "RedactionMode | str" = RedactionMode.MASK,
    **kwargs,
) -> RedactionResult:
    """Detect then redact in one call. kwargs pass through to redact()."""
    return redact(text, DetectionEngine().scan(text), mode, **kwargs)
