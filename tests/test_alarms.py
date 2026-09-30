from datetime import datetime, timezone
from unittest.mock import AsyncMock

import database as db
from alarms import send_alarms
from conftest import run


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def add(chat_id=1, name="Ana", day_month="05/03", birth_year="1990", category="friends", phone=""):
    db.add_birthday(chat_id, name, day_month, birth_year, category, phone)


def test_notifies_at_local_hour_in_spain():
    add(day_month="05/03")
    bot = AsyncMock()
    # 09:00 in Madrid in March (CET, UTC+1) = 08:00 UTC
    assert run(send_alarms(bot, utc(2026, 3, 5, 8, 15))) == 1
    kwargs = bot.send_message.call_args.kwargs
    assert kwargs["chat_id"] == 1 and "Ana" in kwargs["text"] and kwargs["parse_mode"] == "HTML"


def test_does_not_notify_outside_the_hour():
    add(day_month="05/03")
    bot = AsyncMock()
    assert run(send_alarms(bot, utc(2026, 3, 5, 9, 0))) == 0  # 10:00 in Madrid
    bot.send_message.assert_not_awaited()


def test_mexican_user_is_notified_at_their_local_hour():
    db.save_timezone(2, "America/Mexico_City")  # UTC-6 (no daylight saving since 2022)
    add(chat_id=2, day_month="05/03")
    bot = AsyncMock()
    assert run(send_alarms(bot, utc(2026, 3, 5, 8, 0))) == 0   # 02:00 in Mexico
    assert run(send_alarms(bot, utc(2026, 3, 5, 15, 0))) == 1  # 09:00 in Mexico
    assert bot.send_message.call_args.kwargs["chat_id"] == 2


def test_respects_chosen_hour():
    add(day_month="05/03")
    db.save_alarm_hour(1, "18:00")
    bot = AsyncMock()
    assert run(send_alarms(bot, utc(2026, 3, 5, 8, 0))) == 0
    assert run(send_alarms(bot, utc(2026, 3, 5, 17, 0))) == 1


def test_the_day_is_computed_in_the_users_zone():
    db.save_timezone(2, "America/Mexico_City")
    db.save_alarm_hour(2, "21:00")
    add(chat_id=2, day_month="05/03")
    bot = AsyncMock()
    assert run(send_alarms(bot, utc(2026, 3, 5, 3, 0))) == 0   # 21:00 on Mar 4 in Mexico
    assert run(send_alarms(bot, utc(2026, 3, 6, 3, 0))) == 1   # 21:00 on Mar 5 in Mexico


def test_no_duplicates_if_cron_fires_twice():
    add(day_month="05/03")
    bot = AsyncMock()
    assert run(send_alarms(bot, utc(2026, 3, 5, 8, 0))) == 1
    assert run(send_alarms(bot, utc(2026, 3, 5, 8, 30))) == 0
    assert bot.send_message.await_count == 1


def test_force_ignores_hour_and_duplicates():
    add(day_month="05/03")
    bot = AsyncMock()
    assert run(send_alarms(bot, utc(2026, 3, 5, 12, 0), force=True)) == 1
    assert run(send_alarms(bot, utc(2026, 3, 5, 12, 0), force=True)) == 1


def test_one_send_failure_does_not_block_the_rest_and_is_retried():
    add(chat_id=1, name="Blocked", day_month="05/03")
    add(chat_id=2, name="Fine", day_month="05/03")
    bot = AsyncMock()
    bot.send_message.side_effect = [Exception("bot blocked"), None]
    assert run(send_alarms(bot, utc(2026, 3, 5, 8, 0))) == 1
    bot.send_message.side_effect = None
    assert run(send_alarms(bot, utc(2026, 3, 5, 8, 30))) == 1  # retries only the failed one


def test_feb_29_is_announced_on_feb_28_in_non_leap_years():
    add(day_month="29/02", birth_year="2000")
    bot = AsyncMock()
    assert run(send_alarms(bot, utc(2026, 2, 28, 8, 0))) == 1
    assert "26 años" in bot.send_message.call_args.kwargs["text"]


def test_feb_29_in_leap_year_only_on_the_29th():
    add(day_month="29/02", birth_year="2000")
    bot = AsyncMock()
    assert run(send_alarms(bot, utc(2028, 2, 28, 8, 0))) == 0
    assert run(send_alarms(bot, utc(2028, 2, 29, 8, 0))) == 1


def test_several_birthdays_on_the_same_day():
    add(name="A", day_month="05/03")
    add(name="B", day_month="05/03")
    assert run(send_alarms(AsyncMock(), utc(2026, 3, 5, 8, 0))) == 2


def test_notice_uses_the_category_and_age():
    add(name="Ana", day_month="05/03", birth_year="1996", category="partner")
    bot = AsyncMock()
    run(send_alarms(bot, utc(2026, 3, 5, 8, 0)))
    assert "(30 años)" in bot.send_message.call_args.kwargs["text"]


def test_legacy_or_unknown_category_still_works():
    add(day_month="05/03", category="Inventada")
    assert run(send_alarms(AsyncMock(), utc(2026, 3, 5, 8, 0))) == 1


def test_corrupt_date_is_ignored():
    add(name="Broken", day_month="xx")
    add(name="Ok", day_month="05/03")
    assert run(send_alarms(AsyncMock(), utc(2026, 3, 5, 8, 0))) == 1


def test_unknown_zone_is_ignored():
    db.save_timezone(1, "Marte/Base")
    add(day_month="05/03")
    assert run(send_alarms(AsyncMock(), utc(2026, 3, 5, 8, 0))) == 0
