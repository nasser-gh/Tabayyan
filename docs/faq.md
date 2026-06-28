# FAQ

## Why not just use Microsoft Presidio or LLM Guard?

Those are solid, general-purpose tools. Tabayyan is narrow on purpose:

- **Saudi identifiers with real validation.** National ID / Iqama (Luhn
  variant), Saudi IBAN (mod-97), `+966` mobiles, CR, MRN — detected and,
  where a checksum exists, validated. General tools either miss these or
  flag them format-only, producing false positives (see the benchmark).
- **Arabic-aware.** Arabic-Indic digits are normalised; mixed-script and
  Arabic+Latin homograph domains are detected; Arabic names have a
  heuristic detector.
- **Local-first, zero dependencies.** The detection core makes no network
  calls and pulls in no third-party runtime packages.

Use Tabayyan alongside a general tool, not necessarily instead of one.

## Is this enough for PDPL / NDMO compliance?

**No.** It is a detection and redaction *aid*. Compliance is an
organisational outcome involving governance, DPIAs, contracts, access
control, and more. Tabayyan can be one technical control (e.g. redacting
personal data before it reaches an external LLM endpoint) and can produce
evidence, but it is not a compliance certificate.

## How accurate is it?

Checksum-backed types (National ID, Iqama, IBAN, card) have very low
false positives by construction. Context-only types (CR, MRN, Arabic
names) trade recall for precision and are LOW confidence — treat them as
leads, not verdicts. See [Benchmarks](benchmarks.md), and note the
synthetic-data caveat there.

## Will it catch every PII instance?

No. False negatives exist, especially for free-form names, transliterated
names, and institution-specific formats. Do not make it your sole control.

## Does it send data anywhere?

No. The detection core is offline. The only component that touches a
network is a future middleware wrapper, which forwards exactly the
(optionally redacted) payload you choose to send to your LLM endpoint.
