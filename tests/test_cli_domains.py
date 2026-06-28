import json

from tabayyan.cli import main


class _FakeStdin:
    def __init__(self, text):
        self._text = text

    def read(self):
        return self._text



def test_domains_detects_impersonation(tmp_path, capsys, monkeypatch):
    wl = tmp_path / "wl.txt"
    wl.write_text("example.com\nmoh.gov.sa\n")
    monkeypatch.setattr("sys.stdin", _FakeStdin("login at ex\u0430mple.com"))
    main(["domains", "-", "--watchlist", str(wl), "--json"])
    data = json.loads(capsys.readouterr().out)
    findings = data[0]["findings"]
    assert findings and findings[0]["reason"] == "impersonation"


def test_domains_fail_on_find(tmp_path, monkeypatch):
    wl = tmp_path / "wl.txt"
    wl.write_text("example.com\n")
    monkeypatch.setattr("sys.stdin", _FakeStdin("ex\u0430mple.com"))
    rc = main(["domains", "-", "--watchlist", str(wl), "--fail-on-find"])
    assert rc == 1


def test_domains_clean(tmp_path, monkeypatch):
    wl = tmp_path / "wl.txt"
    wl.write_text("example.com\n")
    monkeypatch.setattr("sys.stdin", _FakeStdin("the legit site example.com"))
    rc = main(["domains", "-", "--watchlist", str(wl), "--fail-on-find"])
    assert rc == 0
