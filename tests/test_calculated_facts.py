import re
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest

import database as db
import handlers as h
from age_facts import CALCULATED, FACTS, MAX_FACT_LENGTH, calculated_facts, facts_for_age, format_number, historical_facts, life_values
from alarms import send_alarms
from conftest import make_context, make_update, run
from dates import birth_date

BORN = date(1996, 3, 5)
TODAY = date(2026, 3, 5)  # exactly 30 years and 10,957 days later (7 leap days)


def test_format_number_per_language():
    assert format_number(1234567, "es") == "1.234.567"
    assert format_number(1234567, "en") == "1,234,567"
    assert format_number(401.04, "es", 1) == "401,0"
    assert format_number(401.04, "en", 1) == "401.0"
    assert format_number(15.94, "es", 1) == "15,9"


def test_life_values_use_the_exact_birth_date():
    values = life_values(30, "en", BORN, TODAY)
    assert (TODAY - BORN).days == 10957
    assert values["days"] == "10,957"
    assert values["weeks"] == "1,565"                       # 10957 // 7
    assert values["hours"] == "262,968"                     # 10957 * 24
    assert values["minutes"] == "15,778,080"                # 10957 * 24 * 60
    assert values["seconds"] == "946,684,800"               # 10957 * 86400
    assert values["months"] == "360"
    assert values["orbits"] == "30"
    assert values["km"] == "28,200"                         # 30 * 940 million km
    assert values["moon"] == "401.0"                        # 10957 / 27.3217
    assert values["mars"] == "15.9"                         # 10957 / 686.98 = 15.95
    assert values["mercury"] == "125"                       # 10957 / 87.97
    assert values["jupiter"] == "2.5"                       # 10957 / 4332.59


def test_life_values_without_birth_date_estimate_from_age():
    assert life_values(30, "en")["days"] == "10,957"        # round(30 * 365.2425)
    assert life_values(1, "en")["days"] == "365"


def test_days_are_exact_across_leap_years():
    assert life_values(4, "en", date(2020, 2, 29), date(2024, 2, 29))["days"] == "1,461"
    assert life_values(1, "en", date(2023, 6, 1), date(2024, 6, 1))["days"] == "366"   # includes Feb 29, 2024


def test_calculated_facts_in_spanish_and_english():
    es = calculated_facts(30, "es", BORN, TODAY)
    en = calculated_facts(30, "en", BORN, TODAY)
    assert "Hoy cumples 10.957 días de vida." in es
    assert "Today you turn 10,957 days old." in en
    assert any("946.684.800 segundos" in f for f in es) and any("946,684,800 seconds" in f for f in en)
    assert any("28.200 millones de km" in f for f in es) and any("28,200 million km" in f for f in en)
    assert any("Marte" in f for f in es) and any("Mars" in f for f in en)


def test_calculated_facts_have_no_placeholders_and_are_short():
    for language in ("es", "en"):
        for age in range(1, 121):
            for fact in calculated_facts(age, language, date(2026 - age, 3, 5), TODAY):
                assert not re.search(r"\{\w+\}", fact), fact
                assert len(fact) <= MAX_FACT_LENGTH, fact


def test_both_languages_have_a_template_for_every_calculated_fact():
    assert all(set(templates) == {"es", "en"} for _, templates in CALCULATED)
    assert len(calculated_facts(30, "es")) == len(calculated_facts(30, "en"))


def test_jupiter_only_appears_from_age_6():
    assert not any("Júpiter" in f for f in calculated_facts(5, "es"))
    assert any("Júpiter" in f for f in calculated_facts(6, "es"))


def test_facts_for_age_combines_historical_and_calculated():
    everything = facts_for_age(30, "en", BORN, TODAY)
    assert set(historical_facts(30, "en")) <= set(everything)
    assert set(calculated_facts(30, "en", BORN, TODAY)) <= set(everything)


def test_calculated_facts_exist_even_for_ages_without_historical_ones():
    assert not any(entry[0] == entry[1] == 98 for entry in FACTS)
    assert len(calculated_facts(98, "es", date(1928, 3, 5), date(2026, 3, 5))) >= 10


def test_birth_date_helper():
    assert birth_date("1996", "05/03") == date(1996, 3, 5)
    assert birth_date("2000", "29/02") == date(2000, 2, 29)
    assert birth_date("", "05/03") is None


def test_greeting_message_can_include_exact_calculated_facts(monkeypatch):
    import messages
    monkeypatch.setattr(messages, 'KIND_WEIGHTS', {'greeting': 0, 'historical': 0, 'calculated': 1})
    texts = {h.build_greeting_message(1, "Ana", "1996", "friends", "", today=TODAY, language="en", day_month="05/03")[0]
             for _ in range(400)}
    assert any("10,957" in t or "946,684,800" in t or "1,565" in t for t in texts)
    assert all("Happy birthday" in t or "Congrats" in t for t in texts)


def test_change_suggestion_uses_the_birth_date(monkeypatch):
    import messages
    monkeypatch.setattr(messages, 'KIND_WEIGHTS', {'greeting': 0, 'historical': 0, 'calculated': 1})
    monkeypatch.setattr(h, "today_for_user", lambda chat_id: TODAY)
    db.add_birthday(1, "Ana", "05/03", "1996", "friends", "")
    db.save_language(1, "en")
    original = h.build_greeting_message(1, "Ana", "1996", "friends", "", today=TODAY, language="en", day_month="05/03")[0]
    seen = set()
    for _ in range(80):
        update = make_update(data="another_1")
        update.callback_query.message.text = original
        run(h.change_suggestion(update, make_context()))
        seen.add(update.callback_query.edit_message_text.call_args.kwargs["text"])
    assert any("10,957" in t or "946,684,800" in t for t in seen)


def test_alarm_message_can_include_exact_days(monkeypatch):
    import messages
    monkeypatch.setattr(messages, 'KIND_WEIGHTS', {'greeting': 0, 'historical': 0, 'calculated': 1})
    db.add_birthday(1, "Ana", "05/03", "1996", "friends", "")
    found = False
    for _ in range(60):
        bot = AsyncMock()
        run(send_alarms(bot, datetime(2026, 3, 5, 8, 0, tzinfo=timezone.utc), force=True))
        if "10.957" in bot.send_message.call_args.kwargs["text"] or "946.684.800" in bot.send_message.call_args.kwargs["text"]:
            found = True
            break
    assert found
