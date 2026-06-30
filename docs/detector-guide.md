# Writing a detector

A guide for contributing a high-quality detector — built-in or third-party.
See [plugins.md](plugins.md) for how to register/ship one, and
[ADR 0006](adr/0006-detector-validator-separation.md) for the detector/validator
split.

## 1. Implement `Detector`

```python
from tabayyan.detectors.base import Detector
from tabayyan.entities import Category, Confidence, EntityType, Match

class MyDetector(Detector):
    name = "my_detector"

    def detect(self, text: str):
        for m in MY_PATTERN.finditer(text):
            yield Match(EntityType.CUSTOM, Category.PERSON, Confidence.MEDIUM,
                        m.start(), m.end(), m.group(0), self.name, label="my_thing")
```

`detect` is **pure**: text in, `Match` objects out, no side effects, no I/O,
no global state. The engine normalizes input and maps offsets back for you —
emit spans relative to the text you receive.

## 2. Satisfy the contract tests

Every default detector must pass `tests/test_contracts.py`, and so should
yours:

- spans are valid and in-bounds: `0 ≤ start ≤ end ≤ len(text)`;
- `entity_type` / `category` / `confidence` are the right enums; `value` is a
  `str`;
- `detect()` is deterministic (same input → same output);
- it never crashes on arbitrary Unicode (the Hypothesis fuzz).

## 3. When to add a validator

If your entity has a **checksum or structural rule**, put a pure function in a
validator module (mirror `tabayyan.checksums`) and call it from `detect()`:

- checksum passes → emit `Confidence.HIGH`;
- strong format, no checksum → `MEDIUM`;
- format-only / ambiguous → `LOW`, and **gate on keyword context** (like CR,
  VAT, passport do) so a bare digit run isn't blindly flagged.

Validators are unit- and property-tested in isolation — keep them side-effect
free.

## 4. Confidence & false-positive pitfalls

- A bare N-digit run is almost never safe to flag at `HIGH` without a checksum
  or context — prefer `LOW` + context gating.
- Watch for **overlap** with stronger detectors (e.g. a 15-digit VAT that is
  also Luhn-valid is claimed by `credit_card`); the engine keeps the
  higher-confidence match. Add a golden-corpus case so the behaviour is locked.
- Anchor numeric patterns with `(?<!\d)…(?!\d)` to avoid matching inside longer
  runs.

## 5. Regex design guidelines

- Use **bounded** quantifiers (`\d{10}`, `{4,20}`), never nested unbounded
  groups over overlapping classes — avoid catastrophic backtracking (ReDoS).
- Rely on the engine's normalization; don't re-implement digit/zero-width
  folding in your pattern.
- Compile patterns once at class scope, not per `detect()` call.

## 6. Performance expectations

- `detect()` is called once per scan over the whole text; keep it roughly
  linear in input length.
- No network, no disk, no model loading inside `detect()`. If you need a
  resource, load it once at construction.

## 7. Add tests

- A focused unit test (positive + a hard negative).
- A golden-corpus entry (`tests/golden/`) if it should be regression-locked.
- The contract tests pick your detector up automatically once it's in the
  default set or registered.
