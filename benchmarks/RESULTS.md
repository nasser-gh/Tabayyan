# Benchmark results

Synthetic corpus, seed=1234, 6300 samples (positives + hard negatives).

> Note: `saudi_vat` recall is below 1.0 because a 15-digit VAT that is coincidentally Luhn-valid is claimed by the higher-confidence `credit_card` detector. The span is still redacted — only the entity *type* differs — so this is a labelling overlap, not a missed PII.

| Entity type | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| credit_card | 300 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| saudi_border_number | 300 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| saudi_iban | 300 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| saudi_iqama | 300 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| saudi_landline | 300 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| saudi_mobile | 300 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| saudi_national_address | 300 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| saudi_national_id | 300 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| saudi_passport | 300 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| saudi_unified_number | 300 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| saudi_vat | 265 | 0 | 35 | 1.000 | 0.883 | 0.938 |
| **macro avg** |  |  |  | **1.000** | **0.989** | **0.994** |

## False positives on hard negatives — naive regex vs Tabayyan

Each row counts how many look-alike decoys (invalid checksum, wrong
leading digit) each approach wrongly flagged. Lower is better.

| Entity type | Naive regex FP | Tabayyan FP | FP eliminated |
|---|---:|---:|---:|
| credit_card | 300 | 0 | 300 |
| saudi_iban | 300 | 0 | 300 |
| saudi_iqama | 300 | 0 | 300 |
| saudi_national_id | 300 | 0 | 300 |

## Evasion robustness — recall on obfuscated identifiers

Checksum-valid National IDs and IBANs hidden behind look-alike
characters. The normalization pre-pass restores detection; without
it, recall collapses. Higher is better.

| Technique | Recall (normalized) | Recall (no normalization) |
|---|---:|---:|
| zero_width | 1.000 | 0.000 |
| arabic_indic | 1.000 | 0.500 |
| fullwidth | 1.000 | 0.000 |
