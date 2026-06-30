"""Detector plugin registry.

Two ways to extend the default detector set without touching the core:

1. **Explicit registration** — register a detector instance, or decorate a
   ``Detector`` subclass::

       from tabayyan import register_detector

       @register_detector
       class MyDetector(Detector):
           ...

       register_detector(MyDetector())   # or an instance

   Registered detectors are picked up by ``DetectionEngine()`` (the default
   set) automatically.

2. **Entry-point discovery** — a third-party package advertises detectors
   under the ``tabayyan.detectors`` entry-point group; calling
   ``discover_plugins()`` loads and registers them.

   Discovery is **opt-in**: because Tabayyan processes sensitive text, it does
   not auto-execute third-party detector code on import. You call
   ``discover_plugins()`` when you want it (the pytest/flake8 mechanism, but
   gated behind an explicit call).
"""
from __future__ import annotations

import importlib.metadata as _im

from .base import Detector

ENTRYPOINT_GROUP = "tabayyan.detectors"

_REGISTERED: list[Detector] = []


def _coerce(obj) -> Detector:
    """Turn a Detector instance or subclass into an instance; reject others."""
    inst = obj() if isinstance(obj, type) else obj
    if not isinstance(inst, Detector):
        raise TypeError(f"expected a Detector subclass or instance, got {obj!r}")
    return inst


def register_detector(target):
    """Register a detector. Usable as ``register_detector(instance)`` or as a
    class decorator (``@register_detector``); returns ``target`` unchanged so
    it composes as a decorator."""
    _REGISTERED.append(_coerce(target))
    return target


def registered_detectors() -> list[Detector]:
    """The detectors registered so far (a copy)."""
    return list(_REGISTERED)


def unregister_all() -> None:
    """Clear the registry (mainly for tests)."""
    _REGISTERED.clear()


def _iter_entry_points(group: str):
    eps = _im.entry_points()
    if hasattr(eps, "select"):  # Python 3.10+
        return list(eps.select(group=group))
    return list(eps.get(group, []))  # Python 3.9


def discover_plugins() -> list[Detector]:
    """Load detectors advertised under the ``tabayyan.detectors`` entry-point
    group and register them. Returns the newly-registered detectors.

    Opt-in by design: third-party detector code runs only when you call this.
    """
    found: list[Detector] = []
    for ep in _iter_entry_points(ENTRYPOINT_GROUP):
        det = _coerce(ep.load())
        _REGISTERED.append(det)
        found.append(det)
    return found
