# Release process

Releases are reproducible from this checklist — no maintainer memory required.
Publishing is automated: pushing a `vX.Y.Z` tag triggers
`.github/workflows/release.yml`, which builds and uploads to PyPI via OIDC
**trusted publishing** (no API token).

## 1. Pre-release verification (local)

```bash
pip install -e ".[dev]"

ruff check .                      # lint
pytest -q                         # full suite — includes:
                                  #   property tests   (tests/test_properties.py)
                                  #   golden regression (tests/test_golden_corpus.py)
                                  #   contract tests    (tests/test_contracts.py)
                                  #   public-API freeze (tests/test_public_api.py)
                                  #   fuzz smoke        (tests/test_fuzz_smoke.py)
python benchmarks/run.py          # sanity-check precision/recall + evasion tables

python -m build                   # wheel + sdist into dist/
pip install twine && twine check dist/*   # metadata/rendering validation
mkdocs build --strict             # docs build cleanly (optional: needs [docs])
```

Static type checking (mypy) is **not yet enforced** — see the post-1.0 roadmap.

## 2. Prepare the release

1. Bump the version in **`pyproject.toml`** and **`src/tabayyan/__init__.py`**
   (keep them identical; `tests/test_public_api.py` asserts SemVer shape).
2. In `CHANGELOG.md`, rename the `## Unreleased` section to `## X.Y.Z`.
3. If detection behaviour changed intentionally, regenerate the golden corpus:
   `python -m tests.golden._generate` (and review the diff).
4. Open a `release/X.Y.Z` PR, get CI green, and merge.

## 3. Publish

1. Create a **GitHub Release** with tag `vX.Y.Z` targeting `main`.
2. The tag push runs `release.yml` → builds → publishes to PyPI (trusted
   publishing). Confirm the `release` workflow's `build` and `publish` jobs are
   green.

## 4. Post-release

- Verify the new version on <https://pypi.org/project/tabayyan/> and that
  `pip install tabayyan==X.Y.Z` resolves.
- Confirm the GitHub Release notes render and link the CHANGELOG.

## Versioning

See [docs/api-stability.md](docs/api-stability.md) for SemVer rules, the
breaking-change definition, and the deprecation policy.
