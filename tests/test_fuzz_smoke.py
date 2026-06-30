"""Fuzz smoke test — runs the fuzz invariants over the seed corpus.

Keeps the harness honest in normal CI (no Atheris needed): every seed must
satisfy the same invariants the coverage-guided fuzzer checks. Also doubles as
the "fuzz smoke test" step in the release checklist.
"""
from pathlib import Path

import pytest

from fuzz.harness import run_bytes

_SEED_DIR = Path(__file__).resolve().parent.parent / "fuzz" / "seeds"
_SEEDS = sorted(
    p for p in _SEED_DIR.iterdir() if p.is_file() and not p.name.startswith("_")
)


def test_seed_corpus_is_present():
    assert _SEEDS, "no fuzz seeds found"


@pytest.mark.parametrize("seed", _SEEDS, ids=[p.name for p in _SEEDS])
def test_seed_holds_pipeline_invariants(seed):
    run_bytes(seed.read_bytes())
