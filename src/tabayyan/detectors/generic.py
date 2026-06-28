"""Generic, locale-independent detectors: email, credit card, IP."""
from __future__ import annotations

import ipaddress
import re
from typing import Iterable

from ..checksums import luhn_is_valid
from ..entities import Category, Confidence, EntityType, Match
from .base import Detector


class EmailDetector(Detector):
    name = "email"
    _pattern = re.compile(r"(?<![A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

    def detect(self, text: str) -> Iterable[Match]:
        for m in self._pattern.finditer(text):
            yield Match(EntityType.EMAIL, Category.CONTACT, Confidence.MEDIUM,
                        m.start(), m.end(), m.group(0), self.name)


class CreditCardDetector(Detector):
    name = "credit_card"
    _pattern = re.compile(r"(?<!\d)(?:\d[ \-]?){12,18}\d(?!\d)")

    def detect(self, text: str) -> Iterable[Match]:
        for m in self._pattern.finditer(text):
            digits = re.sub(r"[ \-]", "", m.group(0))
            if not (13 <= len(digits) <= 19) or not luhn_is_valid(digits):
                continue
            yield Match(EntityType.CREDIT_CARD, Category.FINANCIAL, Confidence.HIGH,
                        m.start(), m.end(), digits, self.name, "Luhn-valid")


class IpAddressDetector(Detector):
    name = "ip_address"
    _candidate = re.compile(r"(?<![\w.])(?:\d{1,3}(?:\.\d{1,3}){3}|[0-9A-Fa-f:]{2,}:[0-9A-Fa-f:]*)(?![\w.])")

    def detect(self, text: str) -> Iterable[Match]:
        for m in self._candidate.finditer(text):
            try:
                ipaddress.ip_address(m.group(0))
            except ValueError:
                continue
            yield Match(EntityType.IP_ADDRESS, Category.NETWORK, Confidence.MEDIUM,
                        m.start(), m.end(), m.group(0), self.name)


GENERIC_DETECTORS = [EmailDetector(), CreditCardDetector(), IpAddressDetector()]
