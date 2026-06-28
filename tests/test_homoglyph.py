from tabayyan.confusables import is_mixed_script, scripts_in, skeleton
from tabayyan.homoglyph import analyze_domain, damerau_levenshtein, extract_domains, scan_text

WL = ["scfhs.gov.sa", "moh.gov.sa", "example.com"]


def _reasons(findings):
    return {(f.reason, f.confidence) for f in findings}


def test_skeleton_folds_cyrillic_to_latin():
    spoof = "ex\u0430mple"  # Cyrillic 'а'
    assert skeleton(spoof) == skeleton("example")
    assert spoof != "example"


def test_cyrillic_impersonation_high():
    spoof = "ex\u0430mple.com"
    findings = analyze_domain(spoof, WL)
    assert ("impersonation", "high") in _reasons(findings)
    assert findings[0].target == "example.com"


def test_digit_letter_confusion_impersonation():
    # 'examp1e' folds (1->l) to 'example'
    assert ("impersonation", "high") in _reasons(analyze_domain("examp1e.com", WL))


def test_transposition_is_typosquat():
    assert ("typosquat", "medium") in _reasons(analyze_domain("exampel.com", WL))


def test_legit_domain_no_finding():
    assert analyze_domain("example.com", WL) == []
    assert analyze_domain("scfhs.gov.sa", WL) == []


def test_mixed_script_label_flagged_without_watchlist():
    findings = analyze_domain("\u0635\u062d\u0629health.com", [])  # Arabic + Latin
    assert ("mixed_script", "medium") in _reasons(findings)


def test_pure_arabic_label_not_mixed():
    assert not is_mixed_script("\u0635\u062d\u0629")  # all Arabic
    assert not is_mixed_script("example")             # all Latin


def test_scripts_in_detects_both():
    assert scripts_in("ex\u0430mple") == {"Latin", "Cyrillic"}


def test_punycode_decoded_before_analysis():
    # xn--80ak6aa92e == Cyrillic 'apple'
    findings = analyze_domain("xn--80ak6aa92e.com", ["apple.com"])
    assert any(f.reason == "impersonation" for f in findings)


def test_damerau_levenshtein():
    assert damerau_levenshtein("apple", "aplle") == 1   # transposition
    assert damerau_levenshtein("abc", "abc") == 0
    assert damerau_levenshtein("abc", "abx") == 1


def test_extract_domains_from_text():
    text = "go to http://example.com and moh.gov.sa now"
    hosts = [h for h, _, _ in extract_domains(text)]
    assert "example.com" in hosts and "moh.gov.sa" in hosts


def test_scan_text_offsets_align():
    text = "visit ex\u0430mple.com here"
    findings = scan_text(text, WL)
    f = findings[0]
    assert text[f.start:f.end] == "ex\u0430mple.com"
