# تبيّن · Tabayyan

Saudi-aware PII detection & redaction for LLM pipelines. Local-first, zero
telemetry, no network calls in the detection core.

```python
from tabayyan import scan, scan_and_redact, RedactionMode

for m in scan("National ID 1158813996 on file"):
    print(m.entity_type.value, m.confidence.value)

print(scan_and_redact("call +966512345678", RedactionMode.MASK).text)
```

See the [CLI](cli.md), [Detectors](detectors.md), and [Benchmarks](benchmarks.md).
