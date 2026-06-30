"""Detector registry."""
from __future__ import annotations

from .base import Detector
from .generic import GENERIC_DETECTORS
from .names import ArabicNameDetector
from .registry import (
    discover_plugins, register_detector, registered_detectors, unregister_all,
)
from .saudi import SAUDI_DETECTORS

# The built-in detectors. Stable across environments (the golden corpus relies
# on it) — third-party detectors are added via register_detector/plugins, not
# baked in here.
DEFAULT_DETECTORS = [*SAUDI_DETECTORS, *GENERIC_DETECTORS, ArabicNameDetector()]


def default_detectors() -> list[Detector]:
    """Built-in detectors plus anything registered via the plugin registry.
    This is what ``DetectionEngine()`` uses when no detectors are passed."""
    return [*DEFAULT_DETECTORS, *registered_detectors()]


__all__ = [
    "Detector", "DEFAULT_DETECTORS", "default_detectors", "SAUDI_DETECTORS",
    "GENERIC_DETECTORS", "ArabicNameDetector",
    "register_detector", "registered_detectors", "discover_plugins", "unregister_all",
]
