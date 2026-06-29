"""Middleware + audit layer.

Sits between an application and an LLM endpoint: scans a prompt, redacts
personal data before it leaves, and emits a structured audit record. The
record is the compensating-control evidence — what was detected, what was
redacted, the data categories involved, and whether the destination
constitutes a cross-border transfer.

Stdlib only. Provider-agnostic: the OpenAI/Azure wrapper is duck-typed and
imports nothing — you pass your own client.

Cross-border logic (the PDPL Art. 29 trigger): if personal data is present
AND the destination endpoint is not in-Kingdom, the call is flagged as a
cross-border transfer event. "In-Kingdom" is determined by a `.sa` host or
an explicit allowlist you configure — until your in-Kingdom endpoint is
live, external endpoints (e.g. *.openai.azure.com) are flagged.
"""
from __future__ import annotations

import json
import warnings
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Callable, Iterable, Sequence
from urllib.parse import urlparse

from .engine import DetectionEngine
from .entities import Category, Match
from .ndmo import classification_summary, classify
from .redaction import RedactionMode, RedactionResult, redact, restore

_PERSONAL_CATEGORIES = {
    Category.NATIONAL_IDENTIFIER, Category.FINANCIAL, Category.CONTACT,
    Category.SENSITIVE_HEALTH, Category.PERSON,
}


def host_of(destination: str | None) -> str | None:
    if not destination:
        return None
    if "://" not in destination:
        destination = "//" + destination
    host = urlparse(destination).hostname
    return host.lower() if host else None


def is_in_kingdom(destination: str | None, allowlist: Sequence[str] = ()) -> bool | None:
    """True/False/None(unknown). A `.sa` host or an allowlisted host is in-Kingdom."""
    host = host_of(destination)
    if host is None:
        return None
    if host.endswith(".sa") or host == "sa":
        return True
    allow = {h.lower() for h in allowlist}
    if host in allow or any(host.endswith("." + h) for h in allow):
        return True
    return False


@dataclass
class AuditRecord:
    timestamp: str
    destination: str | None
    destination_host: str | None
    in_kingdom: bool | None
    cross_border_transfer: bool
    action: str                     # allow | redact | block
    personal_data_present: bool
    health_data_present: bool
    entity_summary: dict            # entity_type -> count
    category_summary: dict          # category -> count
    redacted: bool
    blocked: bool
    data_classification: str | None = None   # highest NDMO level present
    classification_summary: dict = field(default_factory=dict)  # level -> count
    values: list | None = None      # raw values, only if explicitly enabled

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass
class ProtectResult:
    text: str
    audit: AuditRecord
    blocked: bool
    vault: dict = field(default_factory=dict)
    matches: list = field(default_factory=list)


class AuditLog:
    """Append-only audit sink. Writes JSONL to a path and/or a callable."""

    def __init__(self, path: str | None = None, sink: Callable[[AuditRecord], None] | None = None):
        self.path = path
        self.sink = sink
        self.records: list[AuditRecord] = []

    def record(self, rec: AuditRecord) -> None:
        self.records.append(rec)
        if self.path:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(rec.to_json() + "\n")
        if self.sink:
            self.sink(rec)


class Guard:
    """Scan -> decide -> redact/block -> audit.

    block_categories: if any detected entity falls in these categories the
        call is blocked (action='block', text not forwarded).
    block_cross_border: block (instead of redact) when a cross-border
        transfer of personal data would occur.
    """

    def __init__(
        self,
        engine: DetectionEngine | None = None,
        mode: RedactionMode | str = RedactionMode.MASK,
        in_kingdom_hosts: Sequence[str] = (),
        block_categories: Iterable[Category] = (),
        block_cross_border: bool = False,
        audit: AuditLog | None = None,
        record_values: bool = False,
        salt: str = "",
    ) -> None:
        self.engine = engine or DetectionEngine()
        self.mode = RedactionMode(mode)
        self.in_kingdom_hosts = list(in_kingdom_hosts)
        self.block_categories = set(block_categories)
        self.block_cross_border = block_cross_border
        self.audit = audit
        self.record_values = record_values
        self.salt = salt

    def inspect(self, text: str) -> list[Match]:
        return self.engine.scan(text)

    def protect(self, text: str, destination: str | None = None) -> ProtectResult:
        matches = self.engine.scan(text)
        categories = {m.category for m in matches}
        personal = bool(categories & _PERSONAL_CATEGORIES)
        health = Category.SENSITIVE_HEALTH in categories

        in_kingdom = is_in_kingdom(destination, self.in_kingdom_hosts)
        cross_border = bool(personal and in_kingdom is not True and destination is not None)

        block = bool(self.block_categories & categories) or (cross_border and self.block_cross_border)

        vault: dict = {}
        if block:
            # Blocked means "do not forward". We still hand back text for logging
            # context, but it is MASK-redacted, never the raw original: a caller
            # that mistakenly forwards `result.text` must not leak PII. MASK is
            # used regardless of self.mode so this path never needs a salt.
            out_text = redact(text, matches, RedactionMode.MASK).text if matches else text
            action = "block"
            redacted = False
        elif matches:
            result: RedactionResult = redact(text, matches, self.mode, salt=self.salt)
            out_text = result.text
            vault = result.vault
            action = "redact"
            redacted = True
        else:
            out_text = text
            action = "allow"
            redacted = False

        rec = AuditRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            destination=destination,
            destination_host=host_of(destination),
            in_kingdom=in_kingdom,
            cross_border_transfer=cross_border,
            action=action,
            personal_data_present=personal,
            health_data_present=health,
            entity_summary=_count(m.entity_type.value for m in matches),
            category_summary=_count(m.category.value for m in matches),
            redacted=redacted,
            blocked=block,
            data_classification=(c.value if (c := classify(matches)) else None),
            classification_summary=classification_summary(matches),
            values=[m.value for m in matches] if self.record_values else None,
        )
        if self.audit:
            self.audit.record(rec)
        return ProtectResult(text=out_text, audit=rec, blocked=block, vault=vault, matches=matches)

    def protect_messages(self, messages, destination: str | None = None):
        """Redact a list of chat messages. SDK-agnostic building block.

        Handles three content shapes seen across OpenAI/Azure/Anthropic SDKs:
          * str content                      -> redacted
          * list of parts (multimodal)       -> text parts redacted, others kept
          * missing/None content             -> passed through
        Applies to every role (PII can appear in system/tool/assistant text).

        Returns (safe_messages, audits, merged_vault). `audits` is one
        AuditRecord per redacted text span group; `merged_vault` lets you
        restore tokens across the whole exchange (tokenize mode).
        """
        safe: list = []
        audits: list[AuditRecord] = []
        vault: dict = {}
        blocked = False
        for msg in messages:
            content = msg.get("content") if isinstance(msg, dict) else None
            if isinstance(content, str) and content:
                pr = self.protect(content, destination=destination)
                audits.append(pr.audit)
                vault.update(pr.vault)
                blocked = blocked or pr.blocked
                safe.append({**msg, "content": pr.text})
            elif isinstance(content, list):
                new_parts = []
                for part in content:
                    if isinstance(part, dict) and isinstance(part.get("text"), str) and part["text"]:
                        pr = self.protect(part["text"], destination=destination)
                        audits.append(pr.audit)
                        vault.update(pr.vault)
                        blocked = blocked or pr.blocked
                        new_parts.append({**part, "text": pr.text})
                    else:
                        new_parts.append(part)
                safe.append({**msg, "content": new_parts})
            else:
                safe.append(msg)
        return safe, audits, vault, blocked

    # --- provider-agnostic wrapper: one guard, every SDK (duck-typed) ---
    def wrap(self, client, provider: str = "auto", destination: str | None = None,
             restore_response: bool = False):
        """Wrap any LLM client behind the guard and return a uniform proxy.

        The returned object exposes a single ``create(**kwargs)`` method that
        works for every supported provider: it redacts PII in the request,
        invokes the underlying client, and (in tokenize mode) restores tokens
        in the response. The provider is auto-detected by client shape, or set
        explicitly with ``provider="openai" | "anthropic" | <registered>``.

        Built-in adapters cover OpenAI/Azure and Anthropic; add your own with
        ``tabayyan.providers.register_adapter``. For zero magic, call
        ``protect_messages(...)`` and your client yourself.

        Limitations match the underlying SDK: with ``stream=True`` the request
        is redacted but the streamed response is passed through (no restore).
        """
        from .providers import resolve_adapter

        adapter = resolve_adapter(client, provider)
        guard = self

        class _Wrapped:
            provider_name = adapter.name

            def create(self, **kwargs):
                audits, vault, blocked = adapter.redact_request(guard, kwargs, destination)
                if blocked:
                    cats = sorted({c for a in audits for c in a.category_summary})
                    cb = any(a.cross_border_transfer for a in audits)
                    raise PermissionError(
                        f"tabayyan Guard blocked a {'cross-border ' if cb else ''}"
                        f"message containing {cats}"
                    )
                resp = adapter.invoke(client, kwargs)
                if (restore_response and guard.mode is RedactionMode.TOKENIZE
                        and not kwargs.get("stream")):
                    adapter.restore_response(resp, vault)
                return resp

        return _Wrapped()

    # --- reference OpenAI/Azure adapter (duck-typed; imports nothing) ---
    def guard_openai(self, client, destination: str | None = None, restore_response: bool = False):
        """DEPRECATED: use ``wrap(client, provider="openai", ...)`` instead.

        Kept as a thin, backward-compatible OpenAI-style proxy exposing
        ``.chat.completions.create``. New code should prefer ``wrap()``, which
        is provider-agnostic.

        REFERENCE adapter for an OpenAI-style client. Duck-typed.

        IMPORTANT: this is a thin reference wrapper validated against common
        message *shapes*, NOT against a live OpenAI/Azure SDK. For production,
        prefer the stable building block `protect_messages(...)` and call your
        client yourself. Known limitations:
          * Streaming (`stream=True`): the request is still redacted, but the
            streamed response is passed through untouched (no token restore).
          * Response restore works only for non-streaming responses whose
            content is at `resp.choices[i].message.content`.

        `client` must expose `.chat.completions.create(model, messages, ...)`.
        """
        warnings.warn(
            "Guard.guard_openai() is deprecated; use Guard.wrap(client, "
            "provider='openai', ...) instead.",
            DeprecationWarning, stacklevel=2,
        )
        guard = self

        class _Completions:
            def create(self, *, model, messages, **kw):
                safe_messages, _audits, vault, blocked = guard.protect_messages(
                    messages, destination=destination
                )
                if blocked:
                    cats = sorted({c for a in _audits for c in a.category_summary})
                    cb = any(a.cross_border_transfer for a in _audits)
                    raise PermissionError(
                        f"tabayyan Guard blocked a {'cross-border ' if cb else ''}"
                        f"message containing {cats}"
                    )
                resp = client.chat.completions.create(model=model, messages=safe_messages, **kw)
                # Do not attempt to restore into a streaming iterator.
                if restore_response and guard.mode is RedactionMode.TOKENIZE and not kw.get("stream"):
                    _restore_openai_response(resp, vault)
                return resp

        class _Chat:
            completions = _Completions()

        class _Proxy:
            chat = _Chat()

        return _Proxy()


def _restore_openai_response(resp, vault: dict) -> None:
    try:
        for choice in resp.choices:
            msg = choice.message
            if getattr(msg, "content", None):
                msg.content = restore(msg.content, vault)
    except AttributeError:
        pass


def _count(items: Iterable[str]) -> dict:
    out: dict = {}
    for it in items:
        out[it] = out.get(it, 0) + 1
    return out
