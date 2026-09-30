import re
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest
from telegram.ext import ConversationHandler

import database as db
import handlers as h
from age_facts import FACTS, MAX_FACT_LENGTH, facts_for_age
from alarms import send_alarms
from categories import CATEGORY_KEYS
from conftest import edited_keyboard, edited_text, keyboard_data, make_context, make_update, run
from dates import format_day_month
from i18n import COMMAND_DESCRIPTIONS, LANGUAGE_NAMES, STRINGS, SUPPORTED_LANGUAGES, detect_language, t
import messages
from messages import SUGGESTIONS, needs_age, ordinal, pick_suggestion

TODAY = date(2026, 6, 15)
PLACEHOLDER = re.compile(r"\{(\w+)\}")


@pytest.fixture(autouse=True)
def fixed_date(monkeypatch):
    monkeypatch.setattr(h, "today_for_user", lambda chat_id: TODAY)


# ---------- language detection ----------
@pytest.mark.parametrize("code,expected", [
    ("es", "es"), ("es-MX", "es"), ("es_AR", "es"), ("ES", "es"),
    ("en", "en"), ("en-GB", "en"), ("EN-us", "en"),
    ("fr", "en"), ("pt-BR", "en"), ("de", "en"), ("zh-hans", "en"),   # untranslated languages -> English
    (None, "es"), ("", "es"), (123, "es"),                               # no information -> Spanish
])
def test_detect_language(code, expected):
    assert detect_language(code) == expected


# ---------- catalogs ----------
def test_all_languages_have_the_same_keys():
    keys = [set(STRINGS[language]) for language in SUPPORTED_LANGUAGES]
    assert all(k == keys[0] for k in keys), set.union(*keys) - set.intersection(*keys)


def test_placeholders_match_between_languages():
    for key, spanish in STRINGS["es"].items():
        if isinstance(spanish, str):
            english = STRINGS["en"][key]
            assert set(PLACEHOLDER.findall(spanish)) == set(PLACEHOLDER.findall(english)), key


def test_list_entries_have_the_same_shape():
    assert len(STRINGS["es"]["months"]) == len(STRINGS["en"]["months"]) == 12
    assert len(STRINGS["es"]["csv_headers"]) == len(STRINGS["en"]["csv_headers"]) == 5


def test_every_key_used_in_the_code_exists():
    source = "".join(open(f, encoding="utf-8").read() for f in ("handlers.py", "dates.py", "alarms.py"))
    used = set(re.findall(r"""\bt\(\s*\w+,\s*["'](\w+)["']""", source))
    assert used and used <= set(STRINGS["es"]), used - set(STRINGS["es"])


def test_t_formats_and_falls_back_to_spanish_for_unknown_language():
    assert t("en", "name_saved", name="Ana").startswith("I'll save Ana")
    assert t("xx", "name_saved", name="Ana").startswith("Guardaré a Ana")


def test_command_menus_have_the_same_commands_in_the_same_order():
    assert len(COMMAND_DESCRIPTIONS["es"]) == len(COMMAND_DESCRIPTIONS["en"])
    assert [n for n, _ in COMMAND_DESCRIPTIONS["en"]] == ["new", "list", "settings", "export", "cancel", "help"]
    assert all(len(description) <= 256 for language in COMMAND_DESCRIPTIONS.values() for _, description in language)


def test_every_command_has_a_spanish_and_english_name():
    app = h.bot_commands("en")
    assert [c.command for c in app] == ["new", "list", "settings", "export", "cancel", "help"]
    assert all(name in sum((h.CMD_NEW, h.CMD_LIST, h.CMD_SETTINGS, h.CMD_EXPORT, h.CMD_CANCEL, h.CMD_HELP), [])
               for name in (c.command for c in h.bot_commands("es") + app))


# ---------- dates ----------
def test_dates_are_formatted_per_language():
    assert format_day_month("05/03", "es") == "5 de marzo"
    assert format_day_month("05/03", "en") == "March 5"


def test_ordinals():
    assert [ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 30, 101, 111)] == \
        ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "23rd", "30th", "101st", "111th"]


# ---------- greetings and facts in English ----------
@pytest.mark.parametrize("category", CATEGORY_KEYS)
def test_english_greetings(category, monkeypatch):
    monkeypatch.setattr(messages, "KIND_WEIGHTS", {"greeting": 1, "historical": 0, "calculated": 0})
    for _ in range(40):
        text = pick_suggestion(category, "Ana", None, language="en")
        assert "Ana" in text and "{" not in text and not re.search(r"[¡¿]", text)
    with_age = {pick_suggestion(category, "Ana", 33, language="en") for _ in range(300)}
    assert any("33" in t_ or "33rd" in t_ for t_ in with_age)
    assert all("{" not in t_ for t_ in with_age)


def test_english_templates_never_use_a_bad_ordinal(monkeypatch):
    monkeypatch.setattr(messages, "KIND_WEIGHTS", {"greeting": 1, "historical": 0, "calculated": 0})
    for templates in SUGGESTIONS["en"].values():
        assert not any(re.search(r"\{age\}th", t_) for t_ in templates)
    for age in (1, 2, 3, 21, 22, 23):
        for category in CATEGORY_KEYS:
            for _ in range(30):
                text = pick_suggestion(category, "Ana", age, language="en")
                assert not re.search(rf"\b{age}th\b", text)


def test_facts_exist_in_both_languages_with_the_same_ages():
    for age in range(1, 121):
        assert len(facts_for_age(age, "es")) == len(facts_for_age(age, "en"))


def test_english_facts_and_jokes_are_english_and_short():
    for entry in FACTS:
        assert len(entry) == 6 and entry[2] != entry[3] and entry[4] != entry[5]
        assert len(entry[3]) <= MAX_FACT_LENGTH and len(entry[5]) <= 70, entry[3]
        assert "{" not in entry[3].replace("{age}", "") and "{" not in entry[5]
    assert any("Bluey" in f and "older than" in f for f in facts_for_age(30, "en"))
    assert any("Mars" in f for f in facts_for_age(2, "en"))


def test_english_message_fits_the_copy_button():
    for category in CATEGORY_KEYS:
        for age in range(1, 101):
            for _ in range(10):
                assert len(pick_suggestion(category, "María Fernanda", age, language="en")) <= 256


def test_english_historical_message_is_english(monkeypatch):
    monkeypatch.setattr(messages, "KIND_WEIGHTS", {"greeting": 0, "historical": 1, "calculated": 0})
    text = pick_suggestion("friends", "Ana", 35, language="en")
    assert text.startswith(("Happy birthday", "Congrats"))
    assert any(fact in text for fact in facts_for_age(35, "en"))


# ---------- the bot talks in the user's language ----------
def test_language_is_detected_from_telegram_and_saved():
    update = make_update(text="/start", language_code="en-US")
    run(h.start(update, make_context()))
    assert update.message.reply_text.call_args_list[0].args[0].startswith("Hi! I'm Cumpleping")
    assert db.get_settings(1)['language'] == 'en' and db.get_settings(1)['language_set']


def test_spanish_user_gets_spanish_and_untranslated_language_gets_english():
    update = make_update(chat_id=2, text="/start", language_code="es-MX")
    run(h.start(update, make_context()))
    assert update.message.reply_text.call_args_list[0].args[0].startswith("¡Hola!")
    update = make_update(chat_id=3, text="/start", language_code="fr")
    run(h.start(update, make_context()))
    assert update.message.reply_text.call_args_list[0].args[0].startswith("Hi!")


def test_saved_language_wins_over_telegram_language():
    db.save_language(1, "es")
    update = make_update(text="/start", language_code="en")
    run(h.start(update, make_context()))
    assert update.message.reply_text.call_args_list[0].args[0].startswith("¡Hola!")


def test_full_english_creation_flow():
    ctx = make_context()
    lang = "en"
    assert run(h.new_start(make_update(text="/new", language_code=lang), ctx)) == h.NAME
    update = make_update(text="Ana", language_code=lang)
    assert run(h.new_name(update, ctx)) == h.MONTH
    assert "Which month" in update.message.reply_text.call_args.args[0]
    assert "March" in [b.text for row in update.message.reply_text.call_args.kwargs["reply_markup"].inline_keyboard for b in row]
    update = make_update(data="month_03", language_code=lang)
    assert run(h.receive_month(update, ctx)) == h.DAY
    assert edited_text(update) == "Great. Which day?"
    update = make_update(data="day_05", language_code=lang)
    assert run(h.receive_day(update, ctx)) == h.ASK_YEAR
    assert "March 5" in edited_text(update)
    assert run(h.ask_year_callback(make_update(data="no_year", language_code=lang), ctx)) == h.CATEGORY
    update = make_update(data="cat_partner", language_code=lang)
    assert run(h.receive_category(update, ctx)) == h.ASK_PHONE
    update = make_update(data="no_phone", language_code=lang)
    assert run(h.ask_phone_callback(update, ctx)) == ConversationHandler.END
    assert "Saved!" in edited_text(update) and "Partner" in edited_text(update)
    assert db.get_birthdays_by_user(1)[0][4] == "partner"   # stored key is language independent


def test_english_category_keyboard_and_labels():
    labels = [b.text for row in h.categories_keyboard("en").inline_keyboard for b in row]
    assert "🍻 Friends" in labels and "💕 Partner" in labels
    assert keyboard_data(h.categories_keyboard("en")) == keyboard_data(h.categories_keyboard("es"))


def test_english_list_and_profile():
    db.add_birthday(1, "Ana", "20/06", "1990", "sports", "34600111222")
    db.save_language(1, "en")
    update = make_update(data="list_all")
    run(h.handle_list(update, make_context()))
    assert "All your birthdays" in edited_text(update)
    label = edited_keyboard(update).inline_keyboard[0][0].text
    assert "36 years" in label and "in 5d" in label
    update = make_update(data="view_1")
    run(h.view_profile(update, make_context()))
    text = edited_text(update)
    assert "Ana's profile" in text and "June 20" in text and "turning 36" in text and "Sports" in text
    assert "✏️ Edit" in [b.text for row in edited_keyboard(update).inline_keyboard for b in row]


def test_english_errors_and_prompts():
    db.save_language(1, "en")
    update = make_update(text="x" * 80)
    run(h.new_name(update, make_context()))
    assert "between 1 and 50" in update.message.reply_text.call_args.args[0]
    update = make_update(text="hello")
    run(h.stray_text(update, make_context()))
    assert "didn't understand" in update.message.reply_text.call_args.args[0]
    update = make_update(text="/export")
    run(h.export_command(update, make_context()))
    assert "no saved birthdays" in update.message.reply_text.call_args.args[0]


def test_english_export_headers_and_filename():
    db.add_birthday(1, "Ana", "05/03", "1990", "work", "")
    db.save_language(1, "en")
    ctx = make_context()
    run(h.export_command(make_update(text="/export"), ctx))
    assert ctx.bot.send_document.call_args.kwargs["filename"] == "my_birthdays.csv"
    content = ctx.bot.send_document.call_args.kwargs["document"].decode("utf-8-sig")
    assert content.startswith("Name,Date,Year,Category,Phone") and "Work" in content


def test_english_settings_and_language_switch():
    db.save_language(1, "en")
    update = make_update(text="/settings")
    run(h.settings_command(update, make_context()))
    text = update.message.reply_text.call_args.args[0]
    assert "Settings" in text and "English" in text
    assert "set_language" in keyboard_data(update.message.reply_text.call_args.kwargs["reply_markup"])

    update = make_update(data="set_language")
    run(h.choose_language(update, make_context()))
    assert keyboard_data(edited_keyboard(update)) == ["lang_es", "lang_en"]
    assert [b.text for b in edited_keyboard(update).inline_keyboard[0]] == [LANGUAGE_NAMES["es"], LANGUAGE_NAMES["en"]]

    update = make_update(data="lang_es")
    run(h.save_language_button(update, make_context()))
    assert db.get_settings(1)['language'] == 'es' and edited_text(update) == "✅ Idioma: Español"
    update = make_update(text="/ajustes")
    run(h.settings_command(update, make_context()))
    assert "Ajustes" in update.message.reply_text.call_args.args[0]


def test_invalid_language_button_is_ignored():
    db.save_language(1, "en")
    run(h.save_language_button(make_update(data="lang_xx"), make_context()))
    assert db.get_settings(1)['language'] == 'en'


def test_language_command_shows_the_picker():
    update = make_update(text="/language", language_code="en")
    run(h.language_command(update, make_context()))
    assert keyboard_data(update.message.reply_text.call_args.kwargs["reply_markup"]) == ["lang_es", "lang_en"]


def test_english_zone_picker_and_hour_confirmation():
    db.save_language(1, "en")
    update = make_update(data="set_zone")
    run(h.choose_zone(update, make_context()))
    labels = [b.text for row in edited_keyboard(update).inline_keyboard for b in row]
    assert "🇲🇽 Mexico (Central)" in labels and "🇪🇸 Spain (Mainland)" in labels
    update = make_update(data="hour_21:00")
    run(h.save_hour(update, make_context()))
    assert edited_text(update) == "✅ Done! I'll remind you of birthdays at 21:00 (🇪🇸 Spain (Mainland))."


def test_english_greeting_message_and_another():
    db.add_birthday(1, "Ana", "20/06", "1996", "friends", "")
    db.save_language(1, "en")
    text, keyboard = h.build_greeting_message(1, "Ana", "1996", "friends", "", today=TODAY, language="en")
    assert "BIRTHDAY REMINDER" in text and "Today is <b>Ana</b>'s birthday" in text and "(30 years old)" in text
    assert "Suggestion" in text
    assert "📋 Copy message" in [b.text for row in keyboard.inline_keyboard for b in row]
    update = make_update(data="another_1")
    update.callback_query.message.text = text
    run(h.change_suggestion(update, make_context()))
    assert "BIRTHDAY REMINDER" in edited_text(update) and edited_text(update) != text


def test_every_language_greeting_uses_its_own_button_labels():
    for language, share_label in (("es", "🔵 Compartir TG"), ("en", "🔵 Share on TG")):
        _, keyboard = h.build_greeting_message(1, "Ana", "1990", "friends", "", today=TODAY, language=language)
        assert share_label in [b.text for row in keyboard.inline_keyboard for b in row]


# ---------- notices are sent in the user's language ----------
def test_alarm_is_sent_in_the_users_language():
    db.add_birthday(1, "Ana", "05/03", "1996", "friends", "")
    db.add_birthday(2, "Luis", "05/03", "1996", "friends", "")
    db.save_language(1, "en")
    db.save_language(2, "es")
    bot = AsyncMock()
    assert run(send_alarms(bot, datetime(2026, 3, 5, 8, 0, tzinfo=timezone.utc))) == 2
    texts = {c.kwargs["chat_id"]: c.kwargs["text"] for c in bot.send_message.call_args_list}
    assert "BIRTHDAY REMINDER" in texts[1] and "RECORDATORIO" in texts[2]


def test_alarm_defaults_to_spanish_for_users_without_saved_language():
    db.add_birthday(1, "Ana", "05/03", "1996", "friends", "")
    bot = AsyncMock()
    run(send_alarms(bot, datetime(2026, 3, 5, 8, 0, tzinfo=timezone.utc)))
    assert "RECORDATORIO" in bot.send_message.call_args.kwargs["text"]


# ---------- command aliases ----------
def _command_names(application):
    names = set()
    for group in application.handlers.values():
        for handler in group:
            inner = [handler]
            if isinstance(handler, ConversationHandler):
                inner = list(handler.entry_points) + list(handler.fallbacks)
            for x in inner:
                names |= getattr(x, "commands", set()) or set()
    return names


def test_spanish_and_english_command_aliases_are_registered():
    from telegram.ext import Application

    async def build():
        application = Application.builder().token("123:TEST").build()
        h.register_handlers(application)
        return application
    names = _command_names(run(build()))
    for expected in ("nuevo", "new", "listar", "list", "ajustes", "settings", "exportar", "export", "cancelar", "cancel",
                     "ayuda", "help", "zona", "timezone", "idioma", "language", "start"):
        assert expected in names, expected
