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

## Arabic text prints as garbage / `UnicodeEncodeError` on Windows

That's the Windows console, not Tabayyan — the library handles Arabic fine;
the default terminal code page (cp1252) can't encode it on `print()`. Fix the
environment, not the code:

```powershell
$env:PYTHONIOENCODING = "utf-8"    # PowerShell
set PYTHONIOENCODING=utf-8         # cmd.exe
```

or use Windows Terminal / a UTF-8 locale. Writing results to a file with
`encoding="utf-8"` also sidesteps the console entirely.

## When are Arabic names detected?

The Arabic-name detector is heuristic and **context/particle driven** — it
favours precision over recall. It fires on names carried by triggers or
connectors, and deliberately misses bare names to avoid flagging every Arabic
word:

- ✅ `المريض محمد بن عبدالله القحطاني` — role trigger (`المريض`) + connector (`بن`)
- ✅ `الاسم: عبدالله أحمد` — field label (`الاسم`)
- ⚠️ `عبدالله أحمد` alone — often missed (no trigger); treat name recall as a
  LOW-confidence lead and pair with human review for hospital notes / chat logs.
