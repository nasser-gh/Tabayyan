# CLI

```bash
tabayyan scan <paths|->            # detect entities
tabayyan redact <paths|-> --mode mask|remove|hash|partial
tabayyan domains <paths|-> --watchlist domains.txt
```

Common filters: `--min-confidence {low,medium,high}`, `--only TYPE...`,
`--exclude TYPE...`, `--json`, `--fail-on-find` (non-zero exit for CI).
