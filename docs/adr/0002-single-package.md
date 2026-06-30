# ADR 0002 — One package, not several distributions

**Status:** Accepted

## Context

As the project grew (engine, redaction, middleware, CLI, vault, provider
adapters, Presidio integration), splitting into multiple PyPI distributions
(`tabayyan-core`, `tabayyan-middleware`, …) was considered, to keep the core
minimal.

## Decision

Ship a **single package** with internal layering and **optional extras** for
heavy dependencies (`tabayyan[crypto]`, `tabayyan[presidio]`). The detection
core stays zero-dependency; nothing heavy is imported unless its extra is used.

## Consequences

- No multi-package release management, version skew, or dependency-resolution
  pain for a young (`0.x`) project.
- The "small core" goal is met by **extras + lazy imports**, not by separate
  distributions: `import tabayyan` pulls no third-party code.
- Revisit only if real pressure appears (e.g. the middleware grows a large
  dependency tree that core users shouldn't pay for).
