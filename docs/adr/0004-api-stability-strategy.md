# ADR 0004 — API stability & compatibility strategy

**Status:** Accepted

## Context

Approaching 1.0, downstream users need to know what they can depend on. Without
an explicit contract, any internal refactor risks silently breaking consumers,
and "is this a breaking change?" becomes a judgement call.

## Decision

Adopt **Semantic Versioning** with an explicit, documented surface
([api-stability.md](../api-stability.md)):

- **Stable** = everything re-exported from the top-level `tabayyan` package
  (`__all__`) plus the CLI.
- **Experimental** = adapter wire details, `normalize()`, the NDMO default map,
  Presidio entity names.
- **Internal** = `_`-prefixed names and non-re-exported submodules.

The Stable export set is **frozen by a test** (`tests/test_public_api.py`):
adding or removing a public symbol fails CI until the frozen set is updated
deliberately. Detection *results* are explicitly **not** a frozen API — recall
improvements are not breaking changes (the golden corpus tracks intentional
drift). Removals go through a deprecation cycle with `DeprecationWarning`.

## Consequences

- Accidental public-API changes can't slip through review.
- Detectors can keep improving without being held hostage to "compatibility".
- A small amount of bookkeeping (updating the frozen set) is the price of the
  guarantee — and that update is the signal that a release needs a version
  decision.
