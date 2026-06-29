# Security Policy

## Design guarantees

- **Local-first.** The detection core performs no network calls. It runs
  fully offline / air-gapped.
- **Zero telemetry.** No usage data, no phone-home, no license check.
- **No core dependencies.** The detection engine depends only on the Python
  standard library. Any future external enrichment will be strictly opt-in
  and isolated from the core.

## Scope and limitations

Tabayyan is a **detection aid**, not a compliance guarantee. Detectors have
false negatives and false positives. Do not rely on it as the sole control
for protecting personal or health data. Validate against your own data and
regulatory obligations (PDPL, NDMO, NCA) before operational use.

## Reporting a vulnerability

Please report security issues privately via GitHub Security Advisories
("Report a vulnerability") rather than a public issue. Include a minimal
reproduction. Do **not** include real personal data in any report — use
synthetic values only.
