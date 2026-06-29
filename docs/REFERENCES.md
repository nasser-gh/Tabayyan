# References & algorithm provenance

Tabayyan's validators implement published, verifiable algorithms. Where an
identifier has **no public checksum**, that is stated explicitly and the
detector is marked LOW confidence.

## Checksums

- **Luhn (mod-10)** — used for credit-card PANs. Standard: ISO/IEC 7812-1.
  Cross-validated against `python-stdnum` (`stdnum.luhn`) over 20k random
  samples, and against official card-network TEST PANs (Visa, Mastercard,
  Amex, Discover, JCB, Diners) — see `tests/test_golden_cards.py` and
  `tests/test_cross_validation_stdnum.py`.
- **Saudi National ID / Iqama** — a Luhn-variant over 10 digits (leading
  `1` = citizen, `2` = resident): double even-indexed digits, sum their
  digits, total ≡ 0 mod 10. This is the de-facto community algorithm.
  Tabayyan's implementation is **cross-validated** against an independent,
  widely-used reference and agrees on 100% of a 50k+ random sample (see
  `tests/test_cross_validation.py`):
    - alhazmy13/Saudi-ID-Validator (MIT) —
      https://github.com/alhazmy13/Saudi-ID-Validator
    - algorithm credit: Abdul-Aziz Al-Oraij (http://aziz.oraij.com)
  **It is still not sourced from an authoritative government specification.**
  The cross-check confirms we match the community standard, not that the
  community standard is officially sanctioned. Confirm against an
  authoritative source before production reliance.
- **Saudi IBAN** — ISO 13616 mod-97-10 (ISO 7064). 24 characters:
  `SA` + 2 check digits + 22 BBAN. Cross-validated against
  `python-stdnum` (`stdnum.iban`) on 12k generated SA IBANs plus mutations,
  and against public canonical example IBANs (SA/GB/DE/FR) — see
  `tests/test_golden_iban.py` and `tests/test_cross_validation_stdnum.py`.
  Note: Tabayyan validates the mod-97 checksum and SA length; `python-stdnum`
  additionally knows per-country BBAN structure. They agree on the checksum.

## Confusables / scripts

- **Confusable folding** is a curated, practical subset inspired by the
  Unicode Security Mechanisms confusables data (Unicode Technical Standard
  #39, "confusables.txt"). It is **not** the full Unicode table; it targets
  characters realistically used to spoof Latin/Arabic domains. Extend it via
  config (see `docs/config.md`).
- **Script ranges** are coarse Unicode block ranges, not the full Unicode
  Script property. Sufficient for mixed-script domain detection; not a
  general-purpose script classifier.

## Identifiers with no public checksum

- **Commercial Registration (CR)** — 10 digits, no published check digit.
  Detection is format + keyword context only. LOW confidence.
- **Medical Record Number (MRN)** — institution-specific, no national
  format. Keyword-context only. LOW confidence. Tagged as health data.
- **Arabic personal names** — heuristic gazetteer + context triggers, not
  ML NER. LOW confidence, recall-limited by design.

## Test oracles (dev-only)

- **python-stdnum** (https://arthurdejong.org/python-stdnum/) is used as an
  independent oracle for Luhn and IBAN in the test suite. It is a
  development/test dependency only; the Tabayyan runtime has zero
  third-party dependencies.
