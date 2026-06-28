"""Detector registry."""
from __future__ import annotations

from .base import Detector
from .generic import GENERIC_DETECTORS
from .names import ArabicNameDetector
from .saudi import SAUDI_DETECTORS

DEFAULT_DETECTORS = [*SAUDI_DETECTORS, *GENERIC_DETECTORS, ArabicNameDetector()]

__all__ = ["Detector", "DEFAULT_DETECTORS", "SAUDI_DETECTORS", "GENERIC_DETECTORS",
           "ArabicNameDetector"]
