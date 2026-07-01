"""Redaction engine.

Applies a redaction strategy to detected matches and returns the
sanitised text plus a mapping. Offline and deterministic.

Key correctness rule: replacements are applied right-to-left so that
character offsets of earlier matches stay valid as later (rightmost)
spans are rewritten first.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

from .entities import Match


class RedactionMode(str, Enum):
    MASK = "mask"          # replace with [ENTITY_TYPE]
    REMOVE = "remove"      # delete entirely
    HASH = "hash"          # deterministic truncated SHA-256
    PARTIAL = "partial"    # keep last N chars, mask the rest
    TOKENIZE = "tokenize"  # stable reversible token + vault


@dataclass(frozen=True)
class RedactionItem:
    entity_type: str
    category: str
    confidence: str
    original: str
    replacement: str
    start: int
    end: int


@dataclass
class RedactionResult:
    text: str
    items: list[RedactionItem] = field(default_factory=list)
    vault: dict[str, str] = field(default_factory=dict)  # token -> original (tokenize)

    @property
    def count(self) -> int:
        return len(self.items)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "count": self.count,
            "items": [vars(i) for i in self.items],
            "vault": self.vault,
        }


def _hash_token(value: str, salt: str, length: int) -> str:
    # HMAC (keyed) rather than a bare salt||value digest: the identifiers we
    # hash (e.g. a 10-digit National ID) live in a space small enough to
    # brute-force from the output. A secret key is what makes the token
    # non-reversible; the empty-key case is rejected by `redact()`.
    digest = hmac.new(salt.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"[HASH:{digest[:length]}]"


def _partial_token(value: str, keep_last: int, fill: str) -> str:
    if keep_last <= 0 or keep_last >= len(value):
        return fill * len(value) if keep_last <= 0 else value
    return fill * (len(value) - keep_last) + value[-keep_last:]


def _replacement_for(
    match: Match,
    mode: RedactionMode,
    *,
    salt: str,
    hash_length: int,
    partial_keep_last: int,
    partial_fill: str,
) -> str:
    if mode is RedactionMode.MASK:
        return match.redacted()
    if mode is RedactionMode.REMOVE:
        return ""
    if mode is RedactionMode.HASH:
        return _hash_token(match.value, salt, hash_length)
    if mode is RedactionMode.PARTIAL:
        return _partial_token(match.value, partial_keep_last, partial_fill)
    raise ValueError(f"unknown mode: {mode}")


def redact(
    text: str,
    matches: Sequence[Match],
    mode: RedactionMode | str = RedactionMode.MASK,
    *,
    salt: str = "",
    hash_length: int = 12,
    partial_keep_last: int = 4,
    partial_fill: str = "*",
    keep_last: int | None = None,
) -> RedactionResult:
    """Return a RedactionResult with sanitised text and an item mapping.

    `matches` need not be sorted; overlapping matches should already be
    resolved by the engine, but any residual overlap is skipped defensively.

    HASH mode requires a non-empty `salt` (used as the HMAC key). Without it
    the tokens are trivially reversible by brute force for low-entropy
    identifiers, so an empty salt is rejected rather than silently insecure.

    `keep_last` is an alias for `partial_keep_last`, matching the CLI's
    `--keep-last`; if given it takes precedence.
    """
    if keep_last is not None:
        partial_keep_last = keep_last
    mode = RedactionMode(mode)
    if mode is RedactionMode.HASH and not salt:
        raise ValueError(
            "HASH redaction requires a non-empty salt (used as the HMAC key); "
            "an empty key leaves short identifiers reversible by brute force."
        )
    ordered = sorted(matches, key=lambda m: m.start)

    # Defensive overlap guard (engine normally resolves these already).
    deduped: list[Match] = []
    last_end = -1
    for m in ordered:
        if m.start < last_end:
            continue
        deduped.append(m)
        last_end = m.end

    # For tokenize: assign a stable token per (type, value) so repeats map
    # to the same token and the mapping is reversible.
    vault: dict[str, str] = {}
    token_for: dict[tuple[str, str], str] = {}
    counters: dict[str, int] = {}

    def tokenize(m: Match) -> str:
        name = m.label or m.entity_type.value
        original = text[m.start:m.end]          # actual span (may differ from m.value)
        key = (name, original)
        if key not in token_for:
            counters[name] = counters.get(name, 0) + 1
            tok = f"<{name.upper()}_{counters[name]}>"
            token_for[key] = tok
            vault[tok] = original                # restore must reproduce the original
        return token_for[key]

    items: list[RedactionItem] = []
    out = text
    # Apply right-to-left to preserve earlier offsets.
    for m in sorted(deduped, key=lambda m: m.start, reverse=True):
        if mode is RedactionMode.TOKENIZE:
            replacement = tokenize(m)
        else:
            replacement = _replacement_for(
                m, mode, salt=salt, hash_length=hash_length,
                partial_keep_last=partial_keep_last, partial_fill=partial_fill,
            )
        out = out[: m.start] + replacement + out[m.end :]
        items.append(
            RedactionItem(
                entity_type=m.entity_type.value,
                category=m.category.value,
                confidence=m.confidence.value,
                original=text[m.start:m.end],
                replacement=replacement,
                start=m.start,
                end=m.end,
            )
        )
    items.sort(key=lambda i: i.start)
    return RedactionResult(text=out, items=items, vault=vault)


def restore(text: str, vault: dict[str, str]) -> str:
    """Reverse a tokenize redaction. Longest tokens first to avoid prefix
    collisions (e.g. <X_1> vs <X_10>)."""
    out = text
    for token in sorted(vault, key=len, reverse=True):
        out = out.replace(token, vault[token])
    return out
