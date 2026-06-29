# Changelog

## Unreleased
- **Encrypted vault:** the tokenize vault (token → original — the reversal
  key) can now be persisted password-encrypted via `tabayyan.vault`
  (`save_vault`/`load_vault`, `encrypt_vault`/`decrypt_vault`). Uses the vetted
  `cryptography` library (Fernet + PBKDF2-HMAC-SHA256, 600k iterations) — no
  home-rolled crypto — behind the optional `tabayyan[crypto]` extra, so the
  detection core stays zero-dependency. Files are written `0600`; wrong
  password or tampering raises a clear error.
- **NDMO data classification:** every audit record now carries
  `data_classification` (the highest NDMO sensitivity level among detected
  entities — health → secret, most PII → confidential, org/network → public)
  and a `classification_summary` (level → count). New `tabayyan.ndmo` module
  with `Classification`, `classify()`, `classification_summary()`, and an
  overridable `CATEGORY_CLASSIFICATION` map. Complements the PDPL cross-border
  evidence trail.
- **Provider adapters — one guard, every SDK:** new `Guard.wrap(client,
  provider="auto")` gives a uniform `create(**kwargs)` entry point across LLM
  SDKs, with built-in OpenAI/Azure and **Anthropic** adapters (Anthropic also
  redacts the `system` prompt) and tokenize-restore on responses. Auto-detects
  the provider by client shape; extend to any SDK via
  `tabayyan.providers.register_adapter`. `guard_openai()` is now a deprecated
  alias of `wrap(..., provider="openai")` (still works, warns).
- **Anti-evasion normalization:** an offset-preserving pre-pass
  (`normalize.py`) now runs in the engine before detection — it strips
  zero-width/bidi format characters (Unicode Cf) and folds Arabic-Indic,
  Persian and fullwidth digits (plus per-character NFKC) so evasion via
  invisible or look-alike characters is defeated for **all** detectors, not
  just the Saudi ones. Matches are projected back onto original offsets, so
  redaction still rewrites the real span (invisibles included). Pure-ASCII
  input is unchanged. Opt out with `DetectionEngine(normalize_input=False)`.
- **New Saudi entities:** landline (`+966 1X`), VAT/tax number (ZATCA TRN,
  context-gated), passport, border/visa number, National Address short code,
  and unified establishment number (700) — each format-only and, where
  ambiguous, gated on a keyword context like CR/MRN. Presidio recognizers
  (`SA_VAT`, `SA_PASSPORT`, `SA_BORDER_NUMBER`, `SA_NATIONAL_ADDRESS`,
  `SA_UNIFIED_NUMBER`) added alongside.
- **Security:** `hash` redaction now uses HMAC-SHA256 (keyed) instead of a
  bare `salt||value` digest, and **requires a non-empty salt**. Short
  identifiers (e.g. a 10-digit National ID) were otherwise reversible by
  brute force from the token. CLI exits with a clear error if `--salt` is
  missing in hash mode.
- **Security:** `Guard.protect()` no longer returns the raw original text on a
  blocked call — the returned `text` is MASK-redacted so a caller that
  mistakenly forwards it cannot leak PII.
- **Fix:** audit `timestamp` is now a timezone-aware UTC ISO-8601 value
  (`datetime.now(timezone.utc)`); removed dead `%z`-fallback code.
- **Detection:** Saudi mobile detector now also matches the `00966`
  international prefix.
- Corrected the engine's overlap-resolution complexity note (worst case is
  O(n²) via list.insert, not O(n log n)).

## 0.5.1
- **Fix:** Arabic comma (U+060C) and other Arabic punctuation no longer
  corrupt Arabic-name tokenization (tightened the letter range).
- **Fix:** tokenize/restore now reproduces the original span exactly,
  including Arabic-Indic digits (vault stores the source span, not the
  normalized value).
- **Middleware hardening:** `protect_messages()` building block; handles
  multimodal/list content, system/tool roles, and streaming (request
  redacted, stream passed through). Honest 'reference adapter' disclaimer.
- **Recall benchmark** (`benchmarks/recall.py`): recall under formatting
  noise + an honest context-free section exposing heuristic limits.
- **Arabic README**, before/after showcase, and an interactive notebook.
- Broadened MRN trigger phrasing (recall 0.69 -> 1.0 with context).

## 0.5.0
- **Middleware + audit** (`Guard`, `AuditLog`): scan -> redact/block -> audit
  before a prompt leaves for an LLM endpoint. Cross-border transfer flagging
  (PDPL Art. 29), category-aware blocking, JSONL audit (values withheld by
  default), and a duck-typed OpenAI/Azure wrapper with tokenize-restore.
- **Presidio integration** (`tabayyan[presidio]`): validated Saudi/Arabic
  recognizers (SA_NATIONAL_ID, SA_IQAMA, SA_IBAN, SA_CR, SA_PHONE_NUMBER,
  MEDICAL_RECORD_NUMBER, PERSON, lookalike domains). Complements Presidio;
  parity-tested against the standalone engine. Runtime core stays zero-dep.
- Name detector: added field-label stopwords (الهوية، الآيبان، …) for tighter
  boundaries in record-style text.

## 0.4.2
- **IBAN & Luhn cross-validation**: differential tests against
  `python-stdnum` (dev-only oracle) — Luhn over 20k random samples, IBAN
  over 12k generated Saudi IBANs + mutations.
- **Golden vectors**: official card-network test PANs (Visa, Mastercard,
  Amex, Discover, JCB, Diners) and canonical public example IBANs
  (SA/GB/DE/FR). Runtime stays zero-dependency.

## 0.4.1
- **National ID cross-validation**: validator differentially tested against
  the community reference alhazmy13/Saudi-ID-Validator (MIT; algorithm by
  Abdul-Aziz Al-Oraij) — 100% agreement on a 50k+ random sample. Updated
  REFERENCES.md and the checksum disclaimer accordingly.

## 0.4.0
- **Arabic name detection** (heuristic, context-gated, LOW confidence) — new
  PERSON category; improves recall on health-sector PII.
- **Streaming** large-file scan with overlap windows (`tabayyan scan --stream`,
  `tabayyan.streaming.scan_file`).
- **Reversible tokenize** redaction mode + `restore()` and a token vault.
- **Config** (`--config`, `tabayyan.config.Config`): disable/add detectors,
  custom regex detectors with labels, extend confusables, tune thresholds.
- **Performance**: rewrote overlap resolution from O(n^2) to O(n log n)
  (~110x faster on dense input). Added `benchmarks/perf.py`.
- **Docs**: REFERENCES.md (algorithm provenance), FAQ, threat model, config.
- Golden-vector tests; National ID disclaimer clarifying it is the
  community algorithm, not an authoritative spec.

## 0.3.0
- **Homoglyph / lookalike-domain detection** (opt-in): IDN homograph
  impersonation via confusable skeletons, mixed-script labels
  (incl. Arabic+Latin), and edit-distance typosquats against a watchlist.
  Punycode (`xn--`) labels decoded before analysis. New `tabayyan domains`
  CLI command.
- **Benchmark suite** (`benchmarks/run.py`): precision/recall/F1 on a
  synthetic corpus with hard negatives, plus a naive-regex baseline that
  quantifies the false positives checksum validation eliminates.
- **Adoption**: Dockerfile, pre-commit hook, PyPI release workflow (OIDC
  trusted publishing), MkDocs docs, Makefile.

## 0.2.0
- Redaction engine: mask / remove / hash / partial.
- CLI: `scan` and `redact` with stdin/file/dir input, filters, JSON, exit codes.

## 0.1.0
- Detection core: Saudi (National ID, Iqama, IBAN, CR, mobile, MRN) +
  generic (email, credit card, IP) detectors with checksum validation.
