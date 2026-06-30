"""Public API compatibility tests.

Freezes the Stable surface (per docs/api-stability.md) so an accidental
removal or rename of a public symbol fails CI. Adding or removing a Stable
export is a deliberate change: update FROZEN_PUBLIC_API here in the same PR.
"""
import inspect

import tabayyan

# The exact Stable surface. Changing this set is a public-API change and must
# be intentional (and reflected in the CHANGELOG / SemVer bump).
FROZEN_PUBLIC_API = {
    # functions
    "scan", "scan_and_redact", "redact", "restore", "classify",
    "classification_summary", "is_in_kingdom", "encrypt_vault", "decrypt_vault",
    "save_vault", "load_vault", "register_adapter", "resolve_adapter",
    "register_detector", "registered_detectors", "discover_plugins", "unregister_all",
    # classes
    "DetectionEngine", "Guard", "AuditLog", "AuditRecord", "ProtectResult",
    "Match", "RedactionResult", "RedactionItem", "ProviderAdapter",
    # enums
    "EntityType", "Category", "Confidence", "RedactionMode", "Classification",
    # metadata
    "__version__",
}


def test_public_surface_is_frozen():
    assert set(tabayyan.__all__) == FROZEN_PUBLIC_API


def test_every_public_name_is_importable():
    for name in tabayyan.__all__:
        assert hasattr(tabayyan, name), f"{name} is exported but not importable"


def test_core_function_signatures_are_stable():
    # scan(text)
    assert list(inspect.signature(tabayyan.scan).parameters) == ["text"]
    # scan_and_redact(text, mode=..., **kwargs)
    sr = inspect.signature(tabayyan.scan_and_redact).parameters
    assert "text" in sr and "mode" in sr
    # redact(text, matches, mode=..., *, salt=..., ...)
    rd = inspect.signature(tabayyan.redact).parameters
    assert list(rd)[:3] == ["text", "matches", "mode"]
    # restore(text, vault)
    assert list(inspect.signature(tabayyan.restore).parameters) == ["text", "vault"]


def test_core_enum_values_present():
    # Removing any of these enum values would be a breaking change.
    assert {"mask", "remove", "hash", "partial", "tokenize"} <= {m.value for m in tabayyan.RedactionMode}
    assert {"public", "confidential", "secret", "top_secret"} <= {c.value for c in tabayyan.Classification}
    assert {"saudi_national_id", "saudi_iqama", "saudi_iban"} <= {e.value for e in tabayyan.EntityType}


def test_version_is_semver():
    parts = tabayyan.__version__.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts), tabayyan.__version__
