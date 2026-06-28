# Detectors

| Type | Validation | Confidence |
|---|---|---|
| Saudi National ID / Iqama | Luhn-variant checksum | HIGH |
| Saudi IBAN | ISO 13616 mod-97 | HIGH |
| Credit card | Luhn | HIGH |
| Saudi mobile (`+966`) | format | MEDIUM |
| Email | format | MEDIUM |
| IP address | parser-validated | MEDIUM |
| Commercial Registration | format + keyword context | LOW |
| Medical Record Number | keyword context (health category) | LOW |
| Arabic personal name | heuristic, context-gated | LOW |
| Lookalike / homoglyph domain | skeleton + edit distance (opt-in) | HIGH/MEDIUM |

HIGH is reserved for checksum-backed types. LOW types need contextual
confirmation before action.
