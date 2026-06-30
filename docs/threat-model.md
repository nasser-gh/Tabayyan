# Threat model

Tabayyan's value comes from being precise about what it does and does not do.
This document separates threats it **actively mitigates**, threats that are
**upstream dependencies**, and threats that are **intentionally out of scope**.
Security wording here is deliberately non-absolute: mitigations hold for the
*currently supported* rules, and future Unicode revisions or newly discovered
confusables may introduce cases not yet handled.

## What Tabayyan defends

- **Accidental disclosure of personal data to an LLM endpoint** — by detecting
  and redacting Saudi/PII entities in prompts before they leave your environment.
- **Leakage of PII into logs, tickets, or repos** — via the CLI in CI /
  pre-commit gates (`--fail-on-find`).
- **Homograph / lookalike-domain phishing references** — via the opt-in domain
  detector against a watchlist.
- **Evasion via invisible or look-alike characters** — an offset-preserving
  normalization pre-pass (`normalize.py`) strips Unicode format/bidi characters
  (category `Cf`) and folds Arabic-Indic, Persian and fullwidth digits (plus
  per-character NFKC) before detection. This is **substantially mitigated for
  the supported normalization rules**; matches are projected back onto the
  original span so redaction still rewrites the real text (invisibles included).

## Threat summary

| Threat | Status | Notes |
|---|---|---|
| Zero-width characters | ✅ Mitigated | Removed during normalization (Unicode `Cf`) |
| RTL/LTR & bidi overrides | ✅ Mitigated | Directional controls stripped (`Cf`) |
| Arabic-Indic / Persian / fullwidth digits | ✅ Mitigated | Canonicalized to ASCII before detection |
| NFKC compatibility forms | ✅ Mitigated | Folded per character |
| Unicode confusable **letters** (Cyrillic/Greek lookalikes) | ⚠ Partial | Folded for **domains** via the homoglyph skeleton; **not** folded in free text, so a Cyrillic letter inside a name/email may evade. Numeric identifiers are unaffected (digit confusables are folded) |
| Mixed-script tokens | ⚠ Partial | Flagged for domains; not a normalization step for general text |
| OCR extraction artifacts | ⚪ Upstream dependency | See below |
| PDF text-extraction artifacts | ⚪ Upstream dependency | See below |
| Prompt injection / jailbreak | ❌ Out of scope | Separate LLM-security concern |
| Resource exhaustion (huge inputs) | ⚠ Partial | Streaming recommended; see below |
| Regex catastrophic backtracking (ReDoS) | ✅ By design | Bounded quantifiers, no nested unbounded groups; dedicated fuzzing planned |

Legend: ✅ mitigated for supported rules · ⚠ partial / conditional · ⚪ upstream dependency · ❌ out of scope.

## Upstream dependencies (not out of scope, but bounded by inputs)

- **OCR quality is an upstream dependency.** Tabayyan operates on *extracted
  text*, not document images. Detection quality is therefore bounded by the
  quality of upstream OCR — characters the OCR drops or mangles cannot be
  detected.
- **PDF text-extraction artifacts are upstream.** Tabayyan analyzes the text a
  PDF extractor produces and does not attempt document reconstruction; ligature
  splitting, reordered runs, or missing spaces from the extractor propagate
  into detection.

## Unicode & encoding assumptions

- Tabayyan operates on Python `str` (Unicode). Decoding bytes is the **caller's
  responsibility**; the CLI reads files as UTF-8 with `errors="replace"`, so
  invalid byte sequences become U+FFFD before detection rather than raising.
- Malformed Unicode and lone replacement characters are treated as ordinary
  text — they neither crash detection (see the Hypothesis fuzz contract tests)
  nor are specially interpreted.
- UTF-16 / other encodings must be decoded to `str` by the caller first.

## Resource exhaustion

- Detection is single-pass per detector over the input; memory scales with
  input size for the in-memory API. For multi-megabyte documents, use
  **streaming** (`tabayyan scan --stream`, `tabayyan.streaming.scan_file`) so
  memory stays flat with overlap windows.
- Overlap resolution is O(n²) worst case in the number of *matches* (not bytes);
  in practice n is tiny. See the performance notes in the README.
- Tabayyan does not impose hard input-size limits — bound inputs at your
  ingestion layer if untrusted.

## Regex safety

- Detector patterns are written to **avoid catastrophic backtracking**: bounded
  quantifiers (`\d{10}`, `{4,20}`) and no nested unbounded groups over
  overlapping character classes. The Hypothesis contract tests run every
  detector over arbitrary Unicode without hangs; a dedicated ReDoS fuzz target
  is a planned scheduled job.
- A `--config` file can add **custom** regex detectors. Treat config as code: a
  malicious or naive pattern can reintroduce catastrophic backtracking. Review
  configs from untrusted sources.

## Trust boundaries

- The detection core runs **inside your trust boundary** and stays there: no
  network egress, no telemetry.
- In **tokenize** mode the vault (token → original) is the reversal key. Store
  it with the controls you'd apply to the original data —
  `tabayyan.vault.save_vault()` persists it password-encrypted (Fernet +
  PBKDF2-HMAC-SHA256, via `tabayyan[crypto]`). Treat `hash` output as
  pseudonymous, not anonymous.
- Detector plugins loaded via `discover_plugins()` execute third-party code;
  discovery is opt-in for this reason. Treat installed plugins as trusted code.

## Security guarantees & non-goals

**Guarantees**

- Deterministic detection over supported, normalized text (same input → same
  output; verified by the golden corpus and property tests).
- Checksum-backed types (National ID, Iqama, IBAN, credit card) are validated
  structurally, not merely format-matched.
- No network calls or telemetry in the detection core.

**Non-goals** — Tabayyan is not, and does not try to be:

- a prompt-injection / jailbreak / instruction-following defense;
- an OCR engine or a document-reconstruction tool;
- a guarantee that a detected identifier was actually *issued* (only that it is
  structurally valid where a checksum exists);
- a replacement for downstream security controls (DLP, WAF, output safety).

## Residual risks

- **False negatives** on free-form names, unusual formats, and letter-confusable
  evasion in non-domain text.
- **Checksum-valid but unissued** identifiers pass validation.
- **Synthetic-only benchmark**: published metrics measure detectors against
  designed distributions, not real production traffic.
