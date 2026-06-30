# ADR 0001 — Normalization runs before detection

**Status:** Accepted

## Context

Detectors are regex/format based. Inputs can be obfuscated with characters that
look normal but break a regex: a zero-width space wedged between ID digits,
Arabic-Indic or fullwidth digits, bidi controls inside an IBAN. Handling this
per-detector would mean every detector (including third-party ones) re-implements
the same normalization — and most would forget some of it. Before this change,
only the Saudi detectors folded Arabic-Indic digits; the generic ones didn't.

## Decision

Run a single, central, offset-preserving normalization pass in the engine
**before** any detector sees the text: strip Unicode format/bidi characters
(category `Cf`), fold Arabic-Indic / Persian / fullwidth digits, and apply
per-character NFKC. Detectors run on the clean text; each match is then
projected back onto the **original** offsets so redaction rewrites the real
span (invisibles included).

## Consequences

- Every detector — built-in or plugin — gets evasion resistance for free.
- The offset back-map adds bookkeeping, but keeps redaction correct on the
  original bytes.
- NFKC is applied per character so it never composes across original
  characters, which keeps the back-map exact at the cost of not merging
  base+combining pairs (not an evasion vector for the identifiers we detect).
- Pure-ASCII input normalizes to itself, so the pass is transparent for the
  common case. Opt out with `DetectionEngine(normalize_input=False)`.
