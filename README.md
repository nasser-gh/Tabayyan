## Tabayyan

**Saudi-aware PII detection & redaction for LLM pipelines. Local-first, zero telemetry.**



[![tests](https://github.com/nasser-gh/tabayyan/actions/workflows/tests.yml/badge.svg)](https://github.com/nasser-gh/tabayyan/actions)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

Generic PII scanners are built around Western identifiers and miss Saudi ones —
or flag them with no validation. **Tabayyan** detects Saudi-specific personal
data (National ID, Iqama, Saudi IBAN, CR, VAT, `+966` mobile & landline, passport,
border/visa, National Address, unified 700 number, medical record numbers)
with real checksum validation, then tags each finding by data category and
confidence so you can redact or block before text leaves your environment for an
LLM endpoint.

It runs **fully offline**: no network calls, no telemetry, no external
dependencies in the detection core.
---

## Why it's different

| | Generic PII tools | Tabayyan |
|---|---|---|
| Saudi National ID / Iqama | missed or unvalidated | checksum-validated (HIGH) |
| Saudi IBAN | partial | ISO 13616 mod-97 (HIGH) |
| Arabic-Indic digits (٠-٩) | usually missed | normalised + detected |
| Medical Record Number | generic | health-category, PDPL/NDMO-aware |
| Arabic personal names | usually missed | heuristic detector (opt-precision) |
| Homograph / lookalike domains | rare | Arabic+Latin aware (opt-in) |
| Network calls | sometimes | **never** |

## Status

Public release (v0.7.1). The pre-1.0 version numbers track development
milestones — the CHANGELOG documents each. Expect the API to stabilise
toward 1.0. What's covered by versioning and what's still experimental is
spelled out in [docs/api-stability.md](docs/api-stability.md).

## Install

```bash
pip install tabayyan        # once published to PyPI
# or, from source:
pip install -e ".[dev]"
```

## Quick start

```python
from tabayyan import scan, scan_and_redact, RedactionMode

for m in scan("call +966512345678 — National ID 1010864542 on file"):
    print(m.entity_type.value, m.confidence.value, m.category.value)

# Redact in one step
result = scan_and_redact("National ID 1158813996", RedactionMode.MASK)
print(result.text)  # National ID [SAUDI_NATIONAL_ID]
```

Each result is a `Match` with `entity_type`, `category`, `confidence`
(HIGH / MEDIUM / LOW), character `start`/`end`, the matched `value`, and a
`.redacted()` placeholder.

> **Windows:** if printing Arabic raises `UnicodeEncodeError`, set
> `PYTHONIOENCODING=utf-8` (a console limitation, not the library) — see the
> [FAQ](docs/faq.md).

## CLI

```bash
# detect (table or --json); reads stdin, files, or directories
echo "National ID 1158813996" | tabayyan scan -
tabayyan scan ./docs --json --min-confidence high

# redact: mask | remove | hash | partial
cat note.txt | tabayyan redact - --mode mask
cat note.txt | tabayyan redact - --mode partial --keep-last 4
cat note.txt | tabayyan redact - --mode hash --salt "$SALT"

# CI / pre-commit gate: non-zero exit if anything is found
tabayyan scan ./src --fail-on-find
```

Filters: `--min-confidence {low,medium,high}`, `--only TYPE...`, `--exclude TYPE...`.

## Redaction modes

| Mode | Output for a National ID | Use case |
|------|--------------------------|----------|
| `mask` | `[SAUDI_NATIONAL_ID]` | default; keeps text readable |
| `remove` | *(deleted)* | strip entirely |
| `hash` | `[HASH:f999c93a6934]` | keyed (HMAC), deterministic; correlate without exposing |
| `partial` | `******8153` | keep last N for debugging |

`hash` is HMAC-SHA256 keyed by `--salt` and **requires a non-empty salt** — a
bare digest of a 10-digit identifier is reversible by brute force, so the key
is what makes the token non-reversible. The same value maps to the same token
under a given salt, so you can correlate occurrences without revealing the
value; change the salt to break correlation across datasets. Treat `hash`
output as pseudonymous, not anonymous.

In code:

```python
from tabayyan import scan_and_redact, RedactionMode

result = scan_and_redact(text, RedactionMode.MASK)
print(result.text)   # sanitised
print(result.count)  # entities redacted
print(result.items)  # per-entity mapping
```

## Confidence model

- **HIGH** — passes a published checksum (National ID, Iqama, IBAN, credit card). Very low false-positive rate.
- **MEDIUM** — strong, specific format match with no checksum available (+966 mobile, email).
- **LOW** — format/context only, meaningful false-positive potential (CR, MRN). Confirm before acting.

## Lookalike / homoglyph domains (opt-in)

Beyond PII, Tabayyan can flag domains that impersonate a watchlist using
confusable characters (IDN homograph attacks), mixed scripts (including
Arabic+Latin), or edit-distance typosquats.

```bash
tabayyan domains email.eml --watchlist my-domains.txt
```

```python
from tabayyan.homoglyph import scan_text

scan_text("login at ex\u0430mple.com", ["example.com"])
# -> impersonation (Cyrillic 'a'), target example.com, HIGH
```

This is not in the default PII detector set — construct
`LookalikeDomainDetector(watchlist=...)` or use the `domains` command.

## Benchmarks

Reproducible on a synthetic corpus with hard negatives:

```bash
python benchmarks/run.py --write  # writes benchmarks/RESULTS.md
```

The headline is the false-positive contrast against a naive format-only regex —
checksum validation removes the entire decoy class:

| Entity type | Naive regex FP | Tabayyan FP |
|---|---|---|
| saudi_national_id | 300 | 0 |
| saudi_iqama | 300 | 0 |
| saudi_iban | 300 | 0 |
| credit_card | 300 | 0 |

*(300 invalid-checksum decoys per type. Synthetic data measures detectors
against their design assumptions, not real-world traffic — see the honest
caveat below.)*

The run also reports an **evasion-robustness** section: recall on identifiers
hidden behind zero-width, Arabic-Indic, or fullwidth characters, with the
normalization pre-pass on vs off — recall stays `1.000` normalized and
collapses without it. Full tables in [benchmarks/RESULTS.md](benchmarks/RESULTS.md).

Validators are independently cross-checked: National ID against
[alhazmy13/Saudi-ID-Validator](https://github.com/alhazmy13/Saudi-ID-Validator),
and IBAN + Luhn against python-stdnum plus official card-network test PANs.
See [REFERENCES.md](docs/REFERENCES.md).

## Docker & pre-commit

```bash
# Docker
docker build -t tabayyan:local .
echo "National ID 1158813996" | docker run --rm -i tabayyan:local scan -

# pre-commit: block accidental PII in commits
# add this repo to .pre-commit-config.yaml (see the file in this repo)
```

## Middleware & audit (Azure / OpenAI)

Put a guard in front of your LLM endpoint: redact personal data before it
leaves, and emit an audit trail — including cross-border transfer flagging
(PDPL Art. 29) for endpoints outside the Kingdom.

```python
from tabayyan import Guard, AuditLog, RedactionMode

guard = Guard(in_kingdom_hosts=["llm.myhospital.health.sa"],
              audit=AuditLog(path="audit.jsonl"))
pr = guard.protect("الهوية 1158813996", destination="https://contoso.openai.azure.com")
pr.text                         # redacted before send
pr.audit.cross_border_transfer  # True for external endpoints with personal data
```

Wrap **any** LLM client — OpenAI/Azure or Anthropic, auto-detected — with
`guard.wrap(client, destination=...)`, then call `.create(...)`; PII is redacted
before the request leaves. See [docs/middleware.md](docs/middleware.md).

## Use it inside Presidio

Already on Microsoft Presidio? Add Tabayyan's validated Saudi/Arabic
recognizers with one import:

```bash
pip install "tabayyan[presidio]"
```

```python
from presidio_analyzer import AnalyzerEngine
from tabayyan.integrations.presidio import register_saudi_recognizers

analyzer = AnalyzerEngine()
register_saudi_recognizers(analyzer)  # SA_NATIONAL_ID, SA_IQAMA, SA_IBAN, ...
```

It complements Presidio (adds what it lacks, no duplication) and is
parity-tested against the standalone engine. See
[docs/presidio.md](docs/presidio.md).

## Performance

Single-threaded, default detector set, on synthetic text:

```bash
python benchmarks/perf.py
```

Overlap resolution sorts in O(n log n) and accepts each match with two bisect
lookups; keeping the disjoint set ordered uses `list.insert`, so the worst case
is O(n²) for pathologically dense input (n = matches, not bytes). In practice n
is tiny: a dense 5 MB sample (one entity per ~57 bytes) still scans in under
2 seconds on a typical CPU, and real prose is far sparser. For very large
files, use streaming so memory stays flat:

```bash
tabayyan scan huge.log --stream
```

## Reversible redaction (tokenize)

```python
from tabayyan import scan_and_redact, restore, RedactionMode

r = scan_and_redact("ID 1158813996, again 1158813996", RedactionMode.TOKENIZE)
# "ID <SAUDI_NATIONAL_ID_1>, again <SAUDI_NATIONAL_ID_1>"  (repeats share a token)
assert restore(r.text, r.vault) == "ID 1158813996, again 1158813996"
```

The vault (token → original) is the reversal key — store it as securely as
the source data.

## Extending via config

```json
{ "disable": ["saudi_cr"],
  "custom_detectors": [
    {"label": "employee_id", "pattern": "EMP-\\d{6}",
     "category": "organisation", "confidence": "medium"}] }
```

```bash
tabayyan scan note.txt --config my-config.json
```

See [docs/config.md](docs/config.md), [docs/faq.md](docs/faq.md),
[docs/threat-model.md](docs/threat-model.md), and
[REFERENCES.md](docs/REFERENCES.md) for algorithm provenance.

## Scope and honest limits

Tabayyan is a **detection aid, not a compliance guarantee**.

- Passing a checksum means a value is *structurally valid*, **not** that it was
  ever issued or belongs to a real person.
- The **National ID** validator uses the de-facto community Luhn variant,
  cross-validated against an independent reference (100% agreement on 50k+
  samples) but **not** an authoritative government spec. Confirm before
  production reliance (see docs/REFERENCES.md).
- **Arabic name** detection is a heuristic, not ML NER: recall is limited
  by design to protect precision.
- **CR** has no public checksum; detection is format + keyword context only.
- **MRN** has no national format; detection is keyword-context only and is
  inherently lower precision. It is still tagged as **health data**, which
  carries the strictest handling obligations under PDPL/NDMO — weight it
  accordingly even at LOW detection confidence.
- **False negatives exist.** Do not make this your sole control for personal
  or health data.

## Roadmap

- **v0.1** — detection core + Saudi/generic detectors + tests.
- **v0.2** — redaction modes (mask/remove/hash/partial) + CLI.
- **v0.3** — homoglyph/lookalike-domain detection, benchmark suite, Docker / pre-commit / PyPI / docs.
- **v0.4** — Arabic name detection, streaming large files, reversible tokenize redaction, JSON config + custom detectors, faster bisect-based overlap resolution, references + FAQ + threat-model docs.
- **v0.5** — middleware + audit (cross-border flagging) and Presidio integration (validated Saudi recognizers).
- **v0.6** — six new Saudi entities (VAT, landline, passport, border/visa, National Address, unified 700); offset-preserving anti-evasion normalization; provider-agnostic adapter layer (OpenAI + Anthropic); NDMO data classification in the audit; password-encrypted tokenize vault; expanded precision/recall + evasion-robustness benchmarks; and security hardening (HMAC-keyed hash, block-path leak fix, timezone-aware audit timestamps).
- **v0.7** — detector plugin system (`register_detector` + opt-in `entry_points` discovery); verification & governance: property-based tests, golden corpus + contract tests, frozen public-API + SemVer/deprecation policy; expanded threat model; scheduled fuzzing; and release-engineering docs (RELEASE, compatibility matrix, ADRs, detector guide).
- **v0.7.1** *(current)* — fixes from a community hands-on review: README quick-start National ID checksum fix (+ regression test), `keep_last` alias for the CLI's `--keep-last`, and docs for Windows console encoding and Arabic-name detection scope.
- **Toward 1.0** — the verification, API-stability, and governance foundations are in place; 1.0 is a stabilization milestone rather than a feature one.

### After 1.0

A short list of priorities (not a wishlist):

- improved homoglyph / letter-confusable handling in free text;
- additional regional identifiers;
- enterprise integrations;
- performance and streaming improvements;
- optional static typing (mypy) in CI;
- optional prompt-injection heuristics (isolated module).

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) and the
[detector guide](docs/detector-guide.md). One hard rule: **synthetic data only —
never** commit real personal data. Releases follow [RELEASE.md](RELEASE.md);
supported environments are listed in [docs/compatibility.md](docs/compatibility.md),
and the design rationale lives in the [ADRs](docs/adr/README.md).

## License

Apache-2.0.
