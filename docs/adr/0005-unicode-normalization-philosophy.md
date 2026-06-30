# ADR 0005 — Unicode normalization philosophy

**Status:** Accepted

## Context

"Normalize Unicode" can mean very different things. Aggressive folding (e.g.
mapping every confusable letter to a Latin skeleton, lowercasing, stripping
accents) improves recall against evasion but destroys information and creates
false positives — folding `0`→`o` would break every numeric identifier.

## Decision

Normalize **conservatively and reversibly**, doing only what is safe for the
identifiers we detect:

- strip invisible/format characters (category `Cf`) and soft hyphen;
- fold digit systems (Arabic-Indic, Persian, fullwidth) to ASCII;
- apply per-character NFKC for compatibility forms.

We deliberately do **not** fold look-alike *letters* (Cyrillic/Greek → Latin)
in general text — that lives only in the opt-in homoglyph/domain detector,
which compares confusable skeletons against a watchlist rather than rewriting
content. The threat model documents letter-confusables in free text as a
known ⚠ partial gap rather than over-claiming coverage.

## Consequences

- Numeric identifiers are robust to the realistic evasion vectors (invisible
  characters, alternate digit systems) without false positives.
- Letter-confusable evasion in names/emails is a known limitation, surfaced
  honestly instead of hidden behind aggressive folding.
- Normalization is idempotent and offset-preserving (verified by property
  tests), which keeps redaction correct.
