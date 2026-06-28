# Recall benchmark (noisy synthetic)

seed=2024, 400 samples per type.

| Entity type | Detected | Total | Recall |
|---|---:|---:|---:|
| saudi_national_id | 400 | 400 | 1.000 |
| saudi_iqama | 400 | 400 | 1.000 |
| saudi_iban | 400 | 400 | 1.000 |
| saudi_mobile | 400 | 400 | 1.000 |
| medical_record_number | 400 | 400 | 1.000 |
| arabic_name | 400 | 400 | 1.000 |

## Context-free recall (heuristic types, no trigger present)

These are the honest limits: with no contextual keyword, precision-first detectors miss most/all entities by design.

| Entity type | Detected | Total | Recall | Note |
|---|---:|---:|---:|---|
| arabic_name (no trigger) | 149 | 400 | 0.372 | fires only on name particles (عبد/بن/آل) |
| medical_record_number (no keyword) | 0 | 400 | 0.000 | requires an MRN keyword by design |

*Interpretation: with context, recall is high; without context, heuristic types deliberately stay silent to protect precision. Use checksum-backed types (ID/IBAN/mobile) for high-recall needs.*
