# Benchmarks

Reproducible on a synthetic corpus with hard negatives:

```bash
python benchmarks/run.py --write
```

The headline result is the false-positive comparison against a naive
format-only regex — checksum validation removes the entire decoy class.
See [RESULTS.md](https://github.com/nasser-gh/tabayyan/blob/main/benchmarks/RESULTS.md).

Honest caveat: synthetic data measures the detectors against their design
assumptions, not real-world traffic distribution.
