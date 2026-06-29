import random

import pytest

from tabayyan import Guard, RedactionMode, register_adapter
from tabayyan.providers import resolve_adapter
from tests.synthetic import make_national_id

NID = make_national_id(random.Random(400), "1")


# --- fake clients that mirror each SDK's shape ---

class FakeOpenAI:
    def __init__(self):
        captured = self.captured = {}

        class _Completions:
            def create(self, *, model, messages, **kw):
                captured["messages"] = messages
                # echo last user content back as the assistant message
                content = messages[-1]["content"]
                msg = type("M", (), {"content": content})()
                choice = type("C", (), {"message": msg})()
                return type("R", (), {"choices": [choice]})()

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


class FakeAnthropic:
    def __init__(self):
        captured = self.captured = {}

        class _Messages:
            def create(self, *, model, messages, **kw):
                captured["messages"] = messages
                captured["system"] = kw.get("system")
                text = messages[-1]["content"]
                if isinstance(text, list):  # block form
                    text = next(b["text"] for b in text if b.get("type") == "text")
                block = type("B", (), {"text": text})()
                return type("R", (), {"content": [block]})()

        self.messages = _Messages()


# --- auto-detection ---

def test_auto_detect_openai_vs_anthropic():
    assert resolve_adapter(FakeOpenAI()).name == "openai"
    assert resolve_adapter(FakeAnthropic()).name == "anthropic"


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        resolve_adapter(object(), provider="auto")
    with pytest.raises(ValueError):
        resolve_adapter(FakeOpenAI(), provider="does-not-exist")


# --- redaction flows ---

def test_openai_request_is_redacted():
    client = FakeOpenAI()
    wrapped = Guard().wrap(client)
    assert wrapped.provider_name == "openai"
    wrapped.create(model="gpt", messages=[{"role": "user", "content": f"ID {NID}"}])
    assert NID not in client.captured["messages"][-1]["content"]


def test_anthropic_request_and_system_are_redacted():
    client = FakeAnthropic()
    wrapped = Guard().wrap(client, provider="anthropic")
    wrapped.create(
        model="claude",
        system=f"Caller national id {NID}",
        messages=[{"role": "user", "content": f"my id is {NID}"}],
    )
    assert NID not in client.captured["messages"][-1]["content"]
    assert NID not in client.captured["system"]


def test_block_raises_for_both_providers():
    g = Guard(block_cross_border=True)
    for client in (FakeOpenAI(), FakeAnthropic()):
        wrapped = g.wrap(client, destination="https://contoso.openai.azure.com")
        with pytest.raises(PermissionError):
            wrapped.create(model="m", messages=[{"role": "user", "content": f"ID {NID}"}])


def test_tokenize_restore_roundtrip_openai():
    client = FakeOpenAI()
    wrapped = Guard(mode=RedactionMode.TOKENIZE).wrap(client, restore_response=True)
    resp = wrapped.create(model="gpt", messages=[{"role": "user", "content": f"ID {NID}"}])
    # the echoed (tokenized) response is restored back to the original value
    assert resp.choices[0].message.content.count(NID) == 1


def test_tokenize_restore_roundtrip_anthropic():
    client = FakeAnthropic()
    wrapped = Guard(mode=RedactionMode.TOKENIZE).wrap(client, provider="anthropic", restore_response=True)
    resp = wrapped.create(model="claude", messages=[{"role": "user", "content": f"ID {NID}"}])
    assert resp.content[0].text.count(NID) == 1


def test_register_custom_adapter():
    class EchoClient:
        def __init__(self):
            self.seen = None

        def run(self, **kw):
            self.seen = kw.get("messages")
            return {"ok": True}

    class EchoAdapter:
        name = "echo"

        def matches(self, client):
            return callable(getattr(client, "run", None))

        def redact_request(self, guard, kwargs, destination):
            safe, audits, vault, blocked = guard.protect_messages(
                kwargs.get("messages") or [], destination=destination
            )
            kwargs["messages"] = safe
            return audits, vault, blocked

        def invoke(self, client, kwargs):
            return client.run(**kwargs)

        def restore_response(self, resp, vault):
            return None

    register_adapter(EchoAdapter())
    client = EchoClient()
    wrapped = Guard().wrap(client, provider="echo")
    wrapped.create(messages=[{"role": "user", "content": f"ID {NID}"}])
    assert NID not in client.seen[-1]["content"]


def test_guard_openai_still_works_but_deprecated():
    client = FakeOpenAI()
    with pytest.warns(DeprecationWarning):
        proxy = Guard().guard_openai(client)
    proxy.chat.completions.create(model="gpt", messages=[{"role": "user", "content": f"ID {NID}"}])
    assert NID not in client.captured["messages"][-1]["content"]
