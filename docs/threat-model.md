# Threat model

## What Tabayyan defends

- **Accidental disclosure of personal data to an LLM endpoint.** By
  detecting and redacting Saudi/PII entities in prompts before they leave
  your environment.
- **Leakage of PII into logs, tickets, or repos.** Via the CLI in CI /
  pre-commit gates (`--fail-on-find`).
- **Homograph / lookalike-domain phishing references.** Via the opt-in
  domain detector against a watchlist.
- **Evasion of detection via invisible or look-alike characters.** An
  offset-preserving normalization pre-pass (`normalize.py`) strips
  zero-width/bidi format characters and folds Arabic-Indic, Persian and
  fullwidth digits (plus NFKC compatibility forms) before detection, so a
  zero-width space wedged into an ID or fullwidth digits no longer slip past.
  Matches are projected back onto the original span, so redaction still
  rewrites the real text (invisibles included).

## Trust boundaries

- The detection core runs **inside your trust boundary** and stays there:
  no network egress, no telemetry.
- In **tokenize** mode the vault (token → original) is sensitive: it is the
  reversal key. Store it with the same controls as the original data —
  `tabayyan.vault.save_vault()` persists it password-encrypted (Fernet +
  PBKDF2-HMAC-SHA256, via the `tabayyan[crypto]` extra) so it is not a
  plaintext dict at rest. Treat `hash` output as pseudonymous, not anonymous.
- A `--config` file can add custom regex detectors and extend confusables.
  Treat config as code: a malicious pattern is a denial-of-service risk
  (catastrophic backtracking). Review configs from untrusted sources.

## What Tabayyan does NOT defend

- It is not a DLP platform, not a WAF, not an output-safety filter for LLM
  responses (it can scan responses, but it does not judge toxicity/jailbreak
  success).
- It does not guarantee detection of every entity (false negatives).
- It does not validate that a detected identifier was actually issued — only
  that it is structurally valid where a checksum exists.

## Residual risks

- **False negatives** on free-form names and unusual formats.
- **Checksum-valid but unissued** identifiers pass validation.
- **Synthetic-only benchmark**: published metrics do not model real traffic.
