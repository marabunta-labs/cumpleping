import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ.setdefault("TOKEN", "123:TEST")

import database  # noqa: E402


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Every test gets its own empty SQLite database."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    database.create_database()


def run(coroutine):
    return asyncio.run(coroutine)


def make_update(chat_id=1, text=None, data=None, contact=None, language_code=None):
    """Fake Telegram Update: text message, contact or button press."""
    update = MagicMock()
    update.effective_chat = SimpleNamespace(id=chat_id)
    update.effective_user = SimpleNamespace(language_code=language_code)
    if data is not None:
        query = MagicMock()
        query.data = data
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.edit_message_reply_markup = AsyncMock()
        query.message = MagicMock()
        query.message.text = ""
        update.callback_query = query
        update.message = None
        update.effective_message = query.message
        update.effective_message.reply_text = AsyncMock()
    else:
        update.callback_query = None
        message = MagicMock()
        message.text = text
        message.contact = SimpleNamespace(phone_number=contact) if contact else None
        message.reply_text = AsyncMock()
        update.message = message
        update.effective_message = message
    return update


def make_context(user_data=None, args=None):
    context = MagicMock()
    context.user_data = user_data if user_data is not None else {}
    context.args = args or []
    context.bot = MagicMock()
    context.bot.send_document = AsyncMock()
    context.bot.send_message = AsyncMock()
    return context


def edited_text(update):
    return update.callback_query.edit_message_text.call_args.kwargs["text"]


def keyboard_data(markup):
    """All callback_data / url values of an InlineKeyboardMarkup."""
    return [b.callback_data or b.url for row in markup.inline_keyboard for b in row]


def edited_keyboard(update):
    return update.callback_query.edit_message_text.call_args.kwargs["reply_markup"]
