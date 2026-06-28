"""Throughput benchmark. Reports MB/s and entities/sec for the default engine.

Synthetic text with a realistic entity density. Single-threaded, warm.
Numbers are indicative on the host CPU, not a guarantee.

Run:  python benchmarks/perf.py
"""
from __future__ import annotations

import random
import time

from tabayyan import DetectionEngine
from tests.synthetic import make_iban, make_mobile, make_national_id


def build_text(rng: random.Random, target_bytes: int) -> str:
    chunks = []
    size = 0
    filler = ("the patient was seen in clinic and the report was filed "
              "for review by the attending physician on duty today ")
    while size < target_bytes:
        chunks.append(filler)
        chunks.append(f"id {make_national_id(rng, '1')} iban {make_iban(rng)} "
                      f"mob {make_mobile(rng, '+966')} ")
        size += sum(len(c) for c in chunks[-2:])
    return "".join(chunks)


def main() -> None:
    rng = random.Random(99)
    text = build_text(rng, 5_000_000)  # ~5 MB
    mb = len(text.encode("utf-8")) / 1_000_000
    engine = DetectionEngine()

    # warm
    engine.scan(text[:10000])

    t0 = time.perf_counter()
    matches = engine.scan(text)
    dt = time.perf_counter() - t0

    print(f"input            : {mb:.2f} MB")
    print(f"entities found   : {len(matches)}")
    print(f"wall time        : {dt:.3f} s")
    print(f"throughput       : {mb / dt:.1f} MB/s")
    print(f"detection rate   : {len(matches) / dt:,.0f} entities/s")


if __name__ == "__main__":
    main()
