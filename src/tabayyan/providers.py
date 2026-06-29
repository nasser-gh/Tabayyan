"""Provider adapters — one guard, every LLM SDK.

Each LLM SDK has a different request method and response shape (OpenAI puts
content at ``resp.choices[i].message.content`` and is called via
``chat.completions.create``; Anthropic uses ``messages.create``, a ``system``
field, and ``resp.content[i].text``). Rather than a bespoke wrapper per
provider, an adapter describes *how* to redact a request, invoke the client,
and restore a tokenized response for one SDK shape. ``Guard.wrap()`` then
gives a single, uniform ``.create(**kwargs)`` entry point regardless of
provider — and ``register_adapter`` lets you teach it a new SDK.

Adapters are duck-typed: they import no provider SDK. You pass your own
client. The shared, fully provider-agnostic building block remains
``Guard.protect_messages()`` — call it and your client yourself when you want
no magic at all.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from .redaction import restore


@runtime_checkable
class ProviderAdapter(Protocol):
    name: str

    def matches(self, client) -> bool:
        """True if this adapter understands `client`'s shape (for auto-detect)."""
        ...

    def redact_request(self, guard, kwargs: dict, destination) -> tuple[list, dict, bool]:
        """Redact PII in `kwargs` in place. Returns (audits, vault, blocked)."""
        ...

    def invoke(self, client, kwargs: dict):
        """Call the underlying client with the (already redacted) kwargs."""
        ...

    def restore_response(self, resp, vault: dict) -> None:
        """Restore tokenized values in the response (tokenize mode)."""
        ...


def _redact_text_blocks(guard, blocks, destination, audits, vault):
    """Redact the `text` field of dict-shaped content blocks; keep the rest."""
    out = []
    blocked = False
    for b in blocks:
        if isinstance(b, dict) and isinstance(b.get("text"), str) and b["text"]:
            pr = guard.protect(b["text"], destination=destination)
            audits.append(pr.audit)
            vault.update(pr.vault)
            blocked = blocked or pr.blocked
            out.append({**b, "text": pr.text})
        else:
            out.append(b)
    return out, blocked


class OpenAIAdapter:
    """OpenAI / Azure OpenAI chat-completions shape."""
    name = "openai"

    def matches(self, client) -> bool:
        chat = getattr(client, "chat", None)
        completions = getattr(chat, "completions", None)
        return callable(getattr(completions, "create", None))

    def redact_request(self, guard, kwargs, destination):
        safe, audits, vault, blocked = guard.protect_messages(
            kwargs.get("messages") or [], destination=destination
        )
        kwargs["messages"] = safe
        return audits, vault, blocked

    def invoke(self, client, kwargs):
        return client.chat.completions.create(**kwargs)

    def restore_response(self, resp, vault):
        try:
            for choice in resp.choices:
                msg = choice.message
                if getattr(msg, "content", None):
                    msg.content = restore(msg.content, vault)
        except AttributeError:
            pass


class AnthropicAdapter:
    """Anthropic Messages shape: `messages` + `system`, content as str or blocks."""
    name = "anthropic"

    def matches(self, client) -> bool:
        messages = getattr(client, "messages", None)
        # Distinguish from OpenAI, which nests create under chat.completions.
        return callable(getattr(messages, "create", None)) and getattr(client, "chat", None) is None

    def redact_request(self, guard, kwargs, destination):
        safe, audits, vault, blocked = guard.protect_messages(
            kwargs.get("messages") or [], destination=destination
        )
        kwargs["messages"] = safe
        # The system prompt can carry PII too — redact it whether str or blocks.
        system = kwargs.get("system")
        if isinstance(system, str) and system:
            pr = guard.protect(system, destination=destination)
            kwargs["system"] = pr.text
            audits.append(pr.audit)
            vault.update(pr.vault)
            blocked = blocked or pr.blocked
        elif isinstance(system, list):
            kwargs["system"], sys_blocked = _redact_text_blocks(
                guard, system, destination, audits, vault
            )
            blocked = blocked or sys_blocked
        return audits, vault, blocked

    def invoke(self, client, kwargs):
        return client.messages.create(**kwargs)

    def restore_response(self, resp, vault):
        content = getattr(resp, "content", None)
        if not content:
            return
        for block in content:
            t = getattr(block, "text", None)
            if isinstance(t, str) and t:
                try:
                    block.text = restore(t, vault)
                except AttributeError:
                    pass
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                block["text"] = restore(block["text"], vault)


_REGISTRY: dict[str, ProviderAdapter] = {}


def register_adapter(adapter: ProviderAdapter) -> None:
    """Register a provider adapter (built-in or custom) by its `name`."""
    _REGISTRY[adapter.name] = adapter


def get_adapter(name: str) -> ProviderAdapter:
    return _REGISTRY[name]


def resolve_adapter(client, provider: str = "auto") -> ProviderAdapter:
    """Pick an adapter for `client`. `provider='auto'` duck-types it."""
    if provider != "auto":
        try:
            return _REGISTRY[provider]
        except KeyError:
            raise ValueError(
                f"unknown provider {provider!r}; registered: {sorted(_REGISTRY)}"
            ) from None
    for adapter in _REGISTRY.values():
        if adapter.matches(client):
            return adapter
    raise ValueError(
        "could not auto-detect a provider for this client; pass provider=... "
        f"(registered: {sorted(_REGISTRY)}) or use Guard.protect_messages() directly"
    )


register_adapter(OpenAIAdapter())
register_adapter(AnthropicAdapter())
