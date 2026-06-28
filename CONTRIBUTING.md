# Contributing

Thanks for your interest in improving Tabayyan.

## Ground rules

1. **No real data, ever.** All fixtures must be synthetic and generated in
   `tests/synthetic.py`. PRs containing real National IDs, IBANs, MRNs, or
   any other real personal data will be rejected.
2. **Keep the core offline.** The detection engine must not introduce network
   calls or non-stdlib runtime dependencies. Optional enrichment belongs in a
   separate, opt-in module.
3. **Be honest about confidence.** A new detector must state HIGH / MEDIUM /
   LOW honestly. HIGH is reserved for checksum-backed types.

## Adding a detector

1. Subclass `Detector` in `src/tabayyan/detectors/`.
2. Return `Match` objects with correct `category` and `confidence`.
3. Register it in `detectors/__init__.py`.
4. Add round-trip tests (valid detected, invalid rejected) using synthetic data.

## Dev setup

```bash
pip install -e ".[dev]"
pytest -q
ruff check .
```
