# Benchmark results

Synthetic corpus, seed=1234, 2700 samples (positives + hard negatives).

| Entity type | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| credit_card | 300 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| saudi_iban | 300 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| saudi_iqama | 300 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| saudi_mobile | 300 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| saudi_national_id | 300 | 0 | 0 | 1.000 | 1.000 | 1.000 |
| **macro avg** |  |  |  | **1.000** | **1.000** | **1.000** |

## False positives on hard negatives — naive regex vs Tabayyan

Each row counts how many look-alike decoys (invalid checksum, wrong
leading digit) each approach wrongly flagged. Lower is better.

| Entity type | Naive regex FP | Tabayyan FP | FP eliminated |
|---|---:|---:|---:|
| credit_card | 300 | 0 | 300 |
| saudi_iban | 300 | 0 | 300 |
| saudi_iqama | 300 | 0 | 300 |
| saudi_national_id | 300 | 0 | 300 |
