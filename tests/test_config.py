import json

from tabayyan.config import Config


def _cfg(tmp_path, data):
    f = tmp_path / "c.json"
    f.write_text(json.dumps(data))
    return Config.from_file(f)


def test_disable_detector(tmp_path):
    eng = _cfg(tmp_path, {"disable": ["saudi_cr"]}).build_engine()
    ms = eng.scan("commercial registration 1010123456")
    assert all(m.entity_type.value != "saudi_cr" for m in ms)


def test_custom_detector_with_label(tmp_path):
    eng = _cfg(tmp_path, {"custom_detectors": [
        {"label": "employee_id", "pattern": r"EMP-\d{6}",
         "category": "organisation", "confidence": "medium"}]}).build_engine()
    ms = eng.scan("staff EMP-004521")
    assert len(ms) == 1
    assert ms[0].entity_type.value == "custom"
    assert ms[0].label == "employee_id"
    assert ms[0].redacted() == "[EMPLOYEE_ID]"


def test_confusables_extension(tmp_path):
    # Extend with a confusable, then check skeleton folding picks it up.
    _cfg(tmp_path, {"confusables": {"\u24e5": "v"}})  # circled v -> v
    from tabayyan.confusables import skeleton
    assert skeleton("\u24e5pn") == "vpn"


def test_typosquat_distance_passthrough(tmp_path):
    cfg = _cfg(tmp_path, {"typosquat_max_distance": 3})
    assert cfg.typosquat_max_distance == 3
