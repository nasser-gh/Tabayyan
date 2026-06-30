# ADR 0003 — Plugin discovery is opt-in

**Status:** Accepted

## Context

Detectors can be extended via a registry (`register_detector`) and via
setuptools `entry_points` (the `tabayyan.detectors` group), the mechanism
pytest/flake8 use for auto-discovery. Auto-loading every installed plugin on
import is convenient — but Tabayyan processes sensitive text, and a plugin is
arbitrary third-party code that would then run automatically in that context.

## Decision

Entry-point discovery is **opt-in**: `discover_plugins()` loads and registers
advertised detectors only when the application calls it. Explicit
`register_detector(...)` remains available for in-process registration. The
built-in `DEFAULT_DETECTORS` set is never altered by installed packages.

## Consequences

- No third-party detector code runs implicitly on `import tabayyan`.
- Default detection stays deterministic across environments — a stray installed
  plugin cannot silently change results, which keeps the golden corpus stable.
- Slightly less "magic" than pytest-style auto-loading; the trade is
  intentional for a privacy/security tool. Documented in `docs/plugins.md`.
