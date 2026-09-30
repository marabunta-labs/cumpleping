"""Date and age logic (pure: no Telegram, no database)."""
import calendar
from datetime import date

from i18n import DEFAULT_LANGUAGE, t

_DAYS_PER_MONTH = {1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
                   7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}

MIN_YEAR = 1900


def max_days(month):
    """Maximum days of a month (February counts 29 to allow leap-day birthdays)."""
    return _DAYS_PER_MONTH[int(month)]


def parse_day_month(day_month):
    """'05/03' -> (5, 3)"""
    day, month = day_month.split("/")[:2]
    return int(day), int(month)


def month_name(month, language=DEFAULT_LANGUAGE):
    """1 -> 'enero' / 'January'"""
    return t(language, "months")[int(month) - 1]


def format_day_month(day_month, language=DEFAULT_LANGUAGE):
    """'05/03' -> '5 de marzo' / 'March 5'"""
    day, month = parse_day_month(day_month)
    return t(language, "date_format", day=day, month=month_name(month, language))


def date_in_year(day, month, year):
    """Birthday date in a given year. Feb 29 is celebrated on Feb 28 in non-leap years."""
    if day == 29 and month == 2 and not calendar.isleap(year):
        return date(year, 2, 28)
    return date(year, month, day)


def next_birthday(day_month, today):
    day, month = parse_day_month(day_month)
    birthday = date_in_year(day, month, today.year)
    if birthday < today:
        birthday = date_in_year(day, month, today.year + 1)
    return birthday


def days_until(day_month, today):
    return (next_birthday(day_month, today) - today).days


def is_birthday_today(day_month, today):
    day, month = parse_day_month(day_month)
    return date_in_year(day, month, today.year) == today


def year_known(birth_year):
    return str(birth_year).isdigit()


def age_on(birth_year, birthday):
    """Age turned on `birthday`, or None if the birth year is unknown."""
    if not year_known(birth_year):
        return None
    age = birthday.year - int(birth_year)
    return age if age > 0 else None


def birth_date(birth_year, day_month):
    """Exact birth date, or None if the birth year is unknown."""
    if not year_known(birth_year):
        return None
    day, month = parse_day_month(day_month)
    return date_in_year(day, month, int(birth_year))


def parse_year(text, today):
    """'1995' -> 1995 if it is a sensible year, otherwise None."""
    text = str(text).strip()
    if len(text) != 4 or not text.isdigit():
        return None
    year = int(text)
    return year if MIN_YEAR <= year <= today.year else None


def date_compatible_with_year(day_month, birth_year):
    """Feb 29 can only belong to someone born in a leap year."""
    if not year_known(birth_year):
        return True
    day, month = parse_day_month(day_month)
    return not (day == 29 and month == 2 and not calendar.isleap(int(birth_year)))
