# ADR 0006 — Detector / validator separation

**Status:** Accepted

## Context

Many PII tools conflate "looks like an ID" with "is a valid ID". Format-only
matching produces large numbers of false positives (any 10-digit run becomes a
"national ID"). Checksums distinguish a structurally valid identifier from a
look-alike — but checksum logic mixed into regex detectors is hard to test and
reuse.

## Decision

Keep **validators pure and separate** from detectors. `tabayyan.checksums`
holds standalone, side-effect-free functions (`saudi_id_is_valid`,
`iban_mod97_is_valid`, `luhn_is_valid`, …). Detectors match candidates by
format, then call a validator to decide confidence: checksum-backed matches are
`HIGH`; format-only matches are `MEDIUM`/`LOW` and, where ambiguous, gated on a
keyword context.

## Consequences

- Validators are trivially unit-testable and property-testable in isolation
  (round-trip and reject-wrong-digit invariants), and are cross-checked against
  independent references (see REFERENCES.md).
- The confidence tiers (`HIGH`/`MEDIUM`/`LOW`) become meaningful and consistent
  across detectors.
- A new detector can reuse existing validators instead of re-deriving checksum
  logic — and inherits the contract tests automatically.
