"""Sending of birthday notices, respecting each user's hour and time zone."""
import logging
from collections import defaultdict
from datetime import datetime, timezone

import pytz

import database as db
from dates import is_birthday_today
from handlers import build_greeting_message

logger = logging.getLogger(__name__)


async def send_alarms(bot, now_utc=None, force=False):
    """Send the notices due right now and return how many were sent.

    A user gets their notices when the local hour of their time zone matches their chosen hour.
    With `force=True` the hour is ignored (for testing). Each birthday is announced once a day.
    """
    now_utc = now_utc or datetime.now(timezone.utc)
    by_user = defaultdict(list)
    for birthday in db.get_all_birthdays():
        by_user[birthday[1]].append(birthday)

    sent = 0
    for chat_id, birthdays in by_user.items():
        settings = db.get_settings(chat_id)
        try:
            local = now_utc.astimezone(pytz.timezone(settings['timezone']))
        except pytz.UnknownTimeZoneError:
            logger.warning("Unknown time zone %r for chat %s", settings['timezone'], chat_id)
            continue
        if not force and local.strftime("%H:00") != settings['hour']:
            continue

        today = local.date()
        for birthday_id, _, name, day_month, birth_year, category, phone in birthdays:
            try:
                if not is_birthday_today(day_month, today):
                    continue
            except (ValueError, IndexError):
                logger.warning("Invalid date %r in birthday %s", day_month, birthday_id)
                continue
            if not force and not db.claim_notice(birthday_id, today.isoformat()):
                continue
            text, keyboard = build_greeting_message(birthday_id, name, birth_year, category, phone, today=today,
                                                    language=settings['language'], day_month=day_month)
            try:
                await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=keyboard)
                sent += 1
            except Exception:
                logger.exception("Could not send %s's notice to chat %s", name, chat_id)
                if not force:
                    db.release_notice(birthday_id, today.isoformat())
    return sent
