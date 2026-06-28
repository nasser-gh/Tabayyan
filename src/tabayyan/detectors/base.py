"""Detector base class. Detectors are pure: text in, matches out."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from ..entities import Match


class Detector(ABC):
    name: str = "detector"

    @abstractmethod
    def detect(self, text: str) -> Iterable[Match]:
        raise NotImplementedError
