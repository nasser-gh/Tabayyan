import json
import random


from tabayyan.cli import main
from tests.synthetic import make_national_id

def test_scan_stdin_table(capsys, monkeypatch):
    nid = make_national_id(random.Random(50), "1")
    monkeypatch.setattr("sys.stdin", _FakeStdin(f"id {nid}"))
    rc = main(["scan"])
    out = capsys.readouterr().out
    assert "saudi_national_id" in out
    assert rc == 0

def test_scan_json(capsys, monkeypatch):
    nid = make_national_id(random.Random(51), "1")
    monkeypatch.setattr("sys.stdin", _FakeStdin(f"id {nid}"))
    main(["scan", "--json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data[0]["matches"][0]["entity_type"] == "saudi_national_id"

def test_fail_on_find_exit_code(capsys, monkeypatch):
    nid = make_national_id(random.Random(52), "1")
    monkeypatch.setattr("sys.stdin", _FakeStdin(f"id {nid}"))
    rc = main(["scan", "--fail-on-find"])
    assert rc == 1

def test_fail_on_find_clean(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", _FakeStdin("clean text"))
    rc = main(["scan", "--fail-on-find"])
    assert rc == 0

def test_redact_stdin(capsys, monkeypatch):
    nid = make_national_id(random.Random(53), "1")
    monkeypatch.setattr("sys.stdin", _FakeStdin(f"id {nid} x"))
    main(["redact", "--mode", "mask"])
    out = capsys.readouterr().out
    assert nid not in out
    assert "[SAUDI_NATIONAL_ID]" in out

def test_min_confidence_filter(capsys, monkeypatch):
    # MRN is LOW; filtering to high should drop it.
    monkeypatch.setattr("sys.stdin", _FakeStdin("MRN: A1234567"))
    main(["scan", "--min-confidence", "high", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data[0]["matches"] == []

def test_file_input(tmp_path, capsys):
    nid = make_national_id(random.Random(54), "1")
    f = tmp_path / "sample.txt"
    f.write_text(f"patient id {nid}")
    main(["scan", str(f)])
    assert "saudi_national_id" in capsys.readouterr().out

def test_directory_batch(tmp_path, capsys):
    rng = random.Random(55)
    (tmp_path / "a.txt").write_text(f"id {make_national_id(rng, '1')}")
    (tmp_path / "b.md").write_text(f"id {make_national_id(rng, '1')}")
    (tmp_path / "ignore.bin").write_text("should be skipped")
    main(["scan", str(tmp_path)])
    out = capsys.readouterr().out
    assert out.count("saudi_national_id") == 2

class _FakeStdin:
    def __init__(self, text):
        self._text = text

    def read(self):
        return self._text
