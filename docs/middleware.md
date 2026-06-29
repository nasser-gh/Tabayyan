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

## Wrapping any LLM client — one guard, every SDK

`Guard.wrap()` returns a uniform proxy with a single `create(**kwargs)` method.
The provider is auto-detected from the client's shape, or set explicitly. PII
in the request (messages **and**, for Anthropic, the `system` prompt) is
redacted before the call.

```python
# OpenAI / Azure (auto-detected)
gpt = guard.wrap(OpenAI(...), destination="https://contoso.openai.azure.com")
gpt.create(model="gpt-4o", messages=[...])

# Anthropic / Claude (auto-detected)
claude = guard.wrap(Anthropic(...))
claude.create(model="claude-sonnet-4-6", system="...", messages=[...])

# Force a provider, or wrap a custom SDK you registered
client = guard.wrap(my_client, provider="anthropic")
```

Built-in adapters cover OpenAI/Azure and Anthropic. Teach it a new SDK with
`register_adapter`:

```python
from tabayyan import register_adapter

class MyAdapter:
    name = "myllm"
    def matches(self, client): ...
    def redact_request(self, guard, kwargs, destination): ...   # returns (audits, vault, blocked)
    def invoke(self, client, kwargs): ...
    def restore_response(self, resp, vault): ...

register_adapter(MyAdapter())
```

With `RedactionMode.TOKENIZE` and `restore_response=True`, the wrapper restores
original values in the model's reply so personalization survives.

For zero magic, the fully provider-agnostic building block is
`guard.protect_messages(messages)` — redact, then call your client yourself.

> `guard_openai()` is **deprecated** in favour of `wrap(client, provider="openai")`;
> it still works (and emits a `DeprecationWarning`).

## NDMO data classification

Every audit record carries `data_classification` — the highest NDMO sensitivity
level among the detected entities — plus a `classification_summary` (level →
count). Health data classifies as **secret**, most PII (IDs, financial,
contact, names) as **confidential**, and org/network identifiers as **public**.

```python
pr = guard.protect("MRN: A1234, ID 1158813996", destination="...")
pr.audit.data_classification   # "secret"  (health outranks the ID)
pr.audit.classification_summary  # {"secret": 1, "confidential": 1}
```

The mapping is a practical default — override `tabayyan.ndmo.CATEGORY_CLASSIFICATION`
to match your own data-classification matrix. Use it directly without the
middleware via `tabayyan.classify(matches)` / `classification_summary(matches)`.

## Audit privacy

Raw values are **not** written to the audit by default (`record_values=False`).
The audit captures counts, categories, and classification — not the data itself.
