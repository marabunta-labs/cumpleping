from datetime import date

import pytest

from dates import (date_compatible_with_year, date_in_year, days_until, age_on, format_day_month,
                   is_birthday_today, max_days, next_birthday, parse_day_month, parse_year)


def test_max_days():
    assert max_days("01") == 31
    assert max_days(4) == 30
    assert max_days("02") == 29


def test_parse_and_format():
    assert parse_day_month("05/03") == (5, 3)
    assert format_day_month("05/03") == "5 de marzo"
    assert format_day_month("31/12") == "31 de diciembre"


def test_feb_29_is_celebrated_on_feb_28_in_non_leap_years():
    assert date_in_year(29, 2, 2025) == date(2025, 2, 28)
    assert date_in_year(29, 2, 2024) == date(2024, 2, 29)


def test_days_until_today_and_future():
    today = date(2026, 3, 1)
    assert days_until("01/03", today) == 0
    assert days_until("02/03", today) == 1


def test_days_until_rolls_over_to_next_year():
    assert days_until("01/01", date(2026, 12, 31)) == 1


def test_days_until_feb_29_does_not_crash_in_non_leap_year():
    assert days_until("29/02", date(2026, 2, 1)) == 27  # falls on Feb 28


def test_next_birthday_feb_29_jumps_to_leap_year_when_due():
    assert next_birthday("29/02", date(2027, 3, 1)) == date(2028, 2, 29)


def test_is_birthday_today():
    assert is_birthday_today("29/02", date(2026, 2, 28))
    assert not is_birthday_today("29/02", date(2024, 2, 28))
    assert is_birthday_today("29/02", date(2024, 2, 29))
    assert not is_birthday_today("10/05", date(2026, 5, 11))


def test_age_on():
    assert age_on("1990", date(2026, 5, 10)) == 36
    assert age_on(1990, date(2026, 5, 10)) == 36
    assert age_on("", date(2026, 5, 10)) is None
    assert age_on("2026", date(2026, 5, 10)) is None  # newborn: 0 years, not shown


@pytest.mark.parametrize("text,expected", [("1995", 1995), (" 2000 ", 2000), ("1899", None), ("2027", None),
                                           ("abcd", None), ("95", None), ("", None), ("2026", 2026)])
def test_parse_year(text, expected):
    assert parse_year(text, date(2026, 6, 1)) == expected


def test_date_compatible_with_year():
    assert date_compatible_with_year("29/02", "2000")
    assert not date_compatible_with_year("29/02", "2001")
    assert date_compatible_with_year("29/02", "")
    assert date_compatible_with_year("28/02", "2001")
