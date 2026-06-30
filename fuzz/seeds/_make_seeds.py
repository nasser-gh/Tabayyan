"""Generate the fuzz seed corpus. Run: python -m fuzz.seeds._make_seeds

A coverage-guided fuzzer is only as good as its seeds. These cover the edge
cases the threat model cares about, so the fuzzer starts from interesting
inputs instead of random noise.
"""
from pathlib import Path

HERE = Path(__file__).parent

SEEDS: dict[str, bytes] = {
    "empty": b"",
    "zero_width": "id 12​34567890 end".encode("utf-8"),
    "bidi_override": "‮evil‬ id 1010‏9999".encode("utf-8"),
    "mixed_arabic_latin": "المريض Mohammed ID 1010 محمد".encode("utf-8"),
    "arabic_indic_digits": "الهوية ١٠١٠".encode("utf-8"),
    "fullwidth_digits": "ID １０１０９".encode("utf-8"),
    "replacement_char": "before�after".encode("utf-8"),
    "malformed_utf8": b"\xff\xfe\x00\x80bad bytes 1010",
    "long_numeric": ("9" * 4096).encode("utf-8"),
    "whitespace_run": (" " * 4096).encode("utf-8"),
    "iban_like": "IBAN SA0380000000608010167519 here".encode("utf-8"),
    "angle_brackets": "value <SAUDI_NATIONAL_ID_1> 1010".encode("utf-8"),
    "newlines_and_tabs": b"line1\n\tID 1010\r\n  IBAN\tSA00",
}


def main() -> None:
    for name, data in SEEDS.items():
        (HERE / name).write_bytes(data)
    print(f"wrote {len(SEEDS)} seeds to {HERE}")


if __name__ == "__main__":
    main()
