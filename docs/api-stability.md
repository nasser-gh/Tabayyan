# API stability & versioning

This document defines what downstream users can rely on, and how changes are
managed as Tabayyan moves toward 1.0.

## Versioning (SemVer)

Tabayyan follows [Semantic Versioning](https://semver.org): `MAJOR.MINOR.PATCH`.

- **Pre-1.0 (`0.x`)** — minor versions *may* contain breaking changes. Every
  one is documented in the [CHANGELOG](../CHANGELOG.md).
- **Post-1.0** —
  - **PATCH** — bug fixes only, no public API change.
  - **MINOR** — backward-compatible additions (new detectors, new entities, new
    optional parameters with defaults).
  - **MAJOR** — breaking changes to a Stable API.

## What counts as a breaking change

A change to a **Stable** API (see below) is breaking if it:

- removes or renames a public symbol, method, or parameter;
- changes a public signature incompatibly (removing/reordering parameters,
  making an optional parameter required);
- changes the type or meaning of a public return value or field;
- removes a value from `EntityType`, `Category`, `Confidence`, `RedactionMode`,
  or `Classification`;
- changes the output format of an existing redaction mode (e.g. the `mask`
  placeholder shape, or the `hash`/tokenize token format).

The following are **not** breaking:

- adding a new detector, `EntityType` value, or redaction behaviour;
- adding a new optional parameter with a default;
- improving detection precision/recall.

> **Detection results are not a frozen API.** Which entities are found for a
> given input improves over time as detectors get better. Intentional changes
> are tracked by the golden corpus (`tests/golden/`), but consumers should not
> hard-code exact detections and treat a recall improvement as a break.

## Stability levels

### Stable

Everything re-exported from the top-level `tabayyan` package (i.e. listed in
`tabayyan.__all__`) plus the CLI. Covered by the SemVer guarantees above.

- **Functions:** `scan`, `scan_and_redact`, `redact`, `restore`, `classify`,
  `classification_summary`, `is_in_kingdom`, `encrypt_vault`, `decrypt_vault`,
  `save_vault`, `load_vault`, `register_adapter`, `resolve_adapter`,
  `register_detector`, `registered_detectors`, `discover_plugins`, `unregister_all`
- **Classes:** `DetectionEngine`, `Guard`, `AuditLog`, `AuditRecord`,
  `ProtectResult`, `Match`, `RedactionResult`, `RedactionItem`, `ProviderAdapter`
- **Enums:** `EntityType`, `Category`, `Confidence`, `RedactionMode`,
  `Classification`
- **CLI:** the `tabayyan` command's subcommands, flags, and exit codes.

The exact public surface is enforced by `tests/test_public_api.py` — adding or
removing a Stable symbol requires a deliberate update there.

### Experimental

Useful and supported, but may change in a MINOR release (with a CHANGELOG
note) without waiting for a MAJOR bump:

- the provider-adapter wire details — the `Guard.wrap` proxy shape and the
  `ProviderAdapter` protocol method signatures;
- the normalization API — `tabayyan.normalize.normalize()` and the `Normalized`
  offset-mapping object;
- the NDMO default mapping `tabayyan.ndmo.CATEGORY_CLASSIFICATION` (levels may
  be re-tuned);
- the Presidio recognizer entity names.

### Internal — no stability guarantee

- anything name-prefixed with `_`;
- submodules not re-exported from the top-level package, e.g.
  `tabayyan.checksums`, `tabayyan.homoglyph`, `tabayyan.confusables`,
  `tabayyan.streaming`, and the detector implementation classes under
  `tabayyan.detectors`;
- the benchmark and test harnesses.

Importing internal modules works, but they may change without notice.

## Deprecation policy

1. A symbol slated for removal is first **deprecated**: it keeps working and
   emits a `DeprecationWarning` naming the replacement (as `Guard.guard_openai`
   does, pointing to `Guard.wrap`).
2. A deprecated API is removed **no earlier than the next MAJOR release**, and
   never in a PATCH.
3. Every deprecation is recorded in the CHANGELOG entry that introduces it.
