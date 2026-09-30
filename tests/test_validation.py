import pytest

from validation import clean_name, normalize_phone


def test_clean_name():
    assert clean_name("  Ana   María ") == "Ana María"
    assert clean_name("   ") is None
    assert clean_name("x" * 51) is None
    assert clean_name("x" * 50) == "x" * 50


@pytest.mark.parametrize("text,expected", [
    ("+34 600 111 222", "34600111222"),
    ("+34-600-111-222", "34600111222"),
    ("0034600111222", "34600111222"),
    ("(52) 55 1234 5678", "525512345678"),
    ("+34", None),
    ("hola", None),
    ("1234567", None),
    ("1" * 16, None),
])
def test_normalize_phone(text, expected):
    assert normalize_phone(text) == expected
