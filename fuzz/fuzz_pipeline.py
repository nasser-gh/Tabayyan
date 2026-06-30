"""Atheris coverage-guided fuzz target for the detection pipeline.

Run locally (Atheris required):

    python -m fuzz.fuzz_pipeline fuzz/seeds -max_total_time=120

The weekly CI workflow runs this bounded and non-blocking, and uploads any
crashing input. Reproduce a crash with `python -m fuzz.replay <crash-file>`.
"""
import sys

import atheris

with atheris.instrument_imports():
    from fuzz.harness import check_text


def _test_one_input(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
    check_text(text)


def main() -> None:
    atheris.Setup(sys.argv, _test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
