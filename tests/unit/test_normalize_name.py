from nhl_hut_bigquery.parser import normalize_name


def test_uppercase_strip_punctuation():
    assert normalize_name("Auston Matthews") == "AUSTON MATTHEWS"


def test_accent_fold():
    assert normalize_name("Patrik Laine") == "PATRIK LAINE"
    assert normalize_name("Léo Carlsson") == "LEO CARLSSON"
    assert normalize_name("Mikaël Hägglund") == "MIKAEL HAGGLUND"


def test_handles_punctuation():
    assert normalize_name("J.T. Miller") == "JT MILLER"
    assert normalize_name("D'Angelo Rondo") == "DANGELO RONDO"


def test_collapses_whitespace():
    assert normalize_name("  John   Doe  ") == "JOHN DOE"


def test_none_returns_none():
    assert normalize_name(None) is None
