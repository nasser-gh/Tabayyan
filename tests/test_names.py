from tabayyan import EntityType, scan


def _names(text):
    return [m.value for m in scan(text) if m.entity_type == EntityType.ARABIC_NAME]


def test_trigger_excludes_title():
    assert _names("اسم المريض عبدالله القحطاني") == ["عبدالله القحطاني"]


def test_particle_run_trims_trailing_verb():
    assert _names("المريض عبد العزيز بن سعد وصل") == ["عبد العزيز بن سعد"]


def test_title_only_no_name():
    assert _names("the meeting room is ready") == []


def test_honorific_dr():
    assert _names("راجعنا د. أحمد الزهراني اليوم") == ["أحمد الزهراني"]


def test_person_category_and_low_confidence():
    ms = [m for m in scan("السيدة نورة آل سعود") if m.entity_type == EntityType.ARABIC_NAME]
    assert ms and ms[0].category.value == "person"
    assert ms[0].confidence.value == "low"


def test_name_followed_by_arabic_comma():
    # Arabic comma (U+060C) must not corrupt the name token.
    assert _names("اسم المريض عبدالله القحطاني، الهوية 1158813996") == ["عبدالله القحطاني"]
