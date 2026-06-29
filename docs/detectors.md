# Detectors

| Type | Validation | Confidence |
|---|---|---|
| Saudi National ID / Iqama | Luhn-variant checksum | HIGH |
| Saudi IBAN | ISO 13616 mod-97 | HIGH |
| Credit card | Luhn | HIGH |
| Saudi mobile (`+966`/`00966`) | format | MEDIUM |
| Saudi landline (`+966 1X`) | format | MEDIUM |
| VAT / tax number (ZATCA TRN) | 15-digit format + keyword context | MEDIUM |
| Email | format | MEDIUM |
| IP address | parser-validated | MEDIUM |
| Commercial Registration | format + keyword context | LOW |
| Passport number | format + keyword context | LOW |
| Border / visa number | format + keyword context | LOW |
| National Address (short code) | format + keyword context | LOW |
| Unified establishment number (700) | format + keyword context | LOW |
| Medical Record Number | keyword context (health category) | LOW |
| Arabic personal name | heuristic, context-gated | LOW |
| Lookalike / homoglyph domain | skeleton + edit distance (opt-in) | HIGH/MEDIUM |

HIGH is reserved for checksum-backed types. LOW types need contextual
confirmation before action.
