# Middleware & audit

`Guard` sits between your application and an LLM endpoint: it scans a prompt,
redacts personal data before it leaves, and emits a structured audit record.
The record is the **compensating-control evidence** — what was detected, what
was redacted, the data categories, and whether the destination is a
cross-border transfer. Stdlib only; the OpenAI/Azure wrapper is duck-typed.

```python
from tabayyan import Guard, AuditLog, RedactionMode

guard = Guard(
    mode=RedactionMode.MASK,
    in_kingdom_hosts=["llm.myhospital.health.sa"],
    audit=AuditLog(path="audit.jsonl"),
)

pr = guard.protect(
    "اسم المريض عبدالله القحطاني، الهوية 1158813996",
    destination="https://contoso.openai.azure.com/v1/chat",
)
print(pr.text)                       # redacted
print(pr.audit.cross_border_transfer)  # True — external endpoint + personal data
print(pr.audit.health_data_present)    # category-aware
```

## Cross-border logic (PDPL Art. 29)

If personal data is present **and** the destination is not in-Kingdom, the
call is flagged as a cross-border transfer. "In-Kingdom" = a `.sa` host or a
host in `in_kingdom_hosts`. Until your in-Kingdom endpoint is live, external
endpoints (e.g. `*.openai.azure.com`) are flagged — exactly the evidence trail
a reviewer expects for a conditional cloud-AI pilot.

## Blocking

```python
from tabayyan.entities import Category

# Block (don't just redact) when sensitive categories would cross the border
guard = Guard(block_cross_border=True)                       # block any cross-border personal data
guard = Guard(block_categories=[Category.SENSITIVE_HEALTH])  # block health data outright
```

## Wrapping an OpenAI / Azure client

```python
client = OpenAI(...)                       # your real client
safe = guard.guard_openai(client, destination="https://contoso.openai.azure.com")
safe.chat.completions.create(model="gpt-4o", messages=[...])  # prompts redacted first
```

With `RedactionMode.TOKENIZE` and `restore_response=True`, the wrapper restores
original values in the model's reply so personalization survives.

## Audit privacy

Raw values are **not** written to the audit by default (`record_values=False`).
The audit captures counts and categories, not the data itself.
