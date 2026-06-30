# Compatibility

## Python

| Version | Status |
|---|---|
| 3.9 | ✅ supported, CI-tested |
| 3.10 | ✅ supported (not in the CI matrix) |
| 3.11 | ✅ supported, CI-tested |
| 3.12 | ✅ supported (not in the CI matrix) |
| 3.13 | ✅ supported, CI-tested |

`requires-python = ">=3.9"`. The CI matrix runs 3.9 / 3.11 / 3.13; the
in-between versions are expected to work and are covered by the same
`>=3.9` language-feature floor.

## Operating systems

| OS | Status |
|---|---|
| Linux | ✅ CI-tested (Ubuntu) |
| macOS | ◻️ expected to work — pure-Python core, no native deps; not CI-tested |
| Windows | ◻️ expected to work — pure-Python core; not CI-tested |

The detection core is pure Python and standard-library only, so platform
differences are minimal. Only the optional `crypto` extra pulls a native
dependency (`cryptography`), which ships wheels for all three platforms.

## Optional integrations & extras

| Extra | Pulls | Minimum | Purpose |
|---|---|---|---|
| _(core)_ | — | — | detection, redaction, middleware — **zero runtime deps** |
| `crypto` | `cryptography` | `>=42` | encrypted tokenize vault (`tabayyan.vault`) |
| `presidio` | `presidio-analyzer` | `>=2.2` | Saudi recognizers inside Microsoft Presidio |
| `docs` | `mkdocs-material` | `>=9` | building the documentation site |
| `dev` | pytest, ruff, build, hypothesis, cryptography, python-stdnum | see `pyproject.toml` | tests, lint, build |

Atheris (fuzzing) is intentionally **not** a declared dependency — the
scheduled fuzz workflow installs it ad hoc and skips if unavailable.

## Stability

What is covered by SemVer vs. experimental vs. internal is documented in
[api-stability.md](api-stability.md).
