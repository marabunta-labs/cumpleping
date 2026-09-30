"""Telegram bot handlers (commands, buttons and conversations)."""
import csv
import html
import io
import logging
import urllib.parse
from datetime import datetime

import pytz
from telegram import BotCommand, CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest, NetworkError
from telegram.ext import (CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler,
                          MessageHandler, filters)

import database as db
from categories import CATEGORY_KEYS, categories, category_label
from dates import (age_on, birth_date, date_compatible_with_year, days_until, format_day_month, max_days, month_name,
                   next_birthday, parse_year, year_known)
from i18n import COMMAND_DESCRIPTIONS, LANGUAGE_NAMES, SUPPORTED_LANGUAGES, detect_language, t
from messages import pick_suggestion
from validation import clean_name, normalize_phone
from zones import ZONES, is_valid_timezone, phone_prefix, timezone_label, zone_options

logger = logging.getLogger(__name__)

# Conversation states (creating and editing share a single ConversationHandler)
(NAME, MONTH, DAY, ASK_YEAR, PICK_YEAR, CATEGORY, ASK_PHONE, ENTER_PHONE,
 E_MENU, E_NAME, E_MONTH, E_DAY, E_YEAR, E_CATEGORY, E_PHONE) = range(15)

PAGE_SIZE = 8
MAX_KEYPAD_PHONE = 16
MAX_COPY_TEXT = 256  # Telegram limit for the "copy" button
CATEGORY_PATTERN = "|".join(CATEGORY_KEYS)

# Every command has a Spanish name and an English alias
CMD_NEW, CMD_LIST, CMD_SETTINGS = ["nuevo", "new"], ["listar", "list"], ["ajustes", "settings"]
CMD_EXPORT, CMD_CANCEL, CMD_HELP = ["exportar", "export"], ["cancelar", "cancel"], ["ayuda", "help"]
CMD_TIMEZONE, CMD_LANGUAGE = ["zona", "timezone"], ["idioma", "language"]


def bot_commands(language):
    """BotCommand list for the Telegram command menu in the given language."""
    return [BotCommand(name, description) for name, description in COMMAND_DESCRIPTIONS[language]]


# --- Helpers ---
def esc(text):
    return html.escape(str(text))


def lang_of(update):
    """The user's language: the saved one, or the one detected from Telegram's language_code (then saved)."""
    chat_id = update.effective_chat.id
    settings = db.get_settings(chat_id)
    if settings['language_set']:
        return settings['language']
    user = getattr(update, "effective_user", None)
    language = detect_language(getattr(user, "language_code", None))
    db.save_language(chat_id, language)
    return language


def today_for_user(chat_id):
    """Today's date in the user's time zone."""
    return datetime.now(pytz.timezone(db.get_settings(chat_id)['timezone'])).date()


async def edit(query, text, reply_markup=None):
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            raise


async def reply(update, text, reply_markup=None):
    """Edit the message if it came from a button; otherwise send a new one."""
    if update.callback_query:
        await edit(update.callback_query, text, reply_markup)
    else:
        await update.effective_message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")


def button(text, data):
    return InlineKeyboardButton(text, callback_data=data)


# --- Reusable keyboards (prefix "" for creating, "e" for editing) ---
def months_keyboard(language, prefix=""):
    rows = [[button(month_name(i, language).capitalize(), f"{prefix}month_{i:02d}") for i in range(start, start + 3)]
            for start in (1, 4, 7, 10)]
    return InlineKeyboardMarkup(rows)


def days_keyboard(month, prefix=""):
    rows, row = [], []
    for i in range(1, max_days(month) + 1):
        row.append(button(str(i), f"{prefix}day_{i:02d}"))
        if len(row) == 7:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def years_keyboard(start, today, prefix="", with_unknown=False, language="es"):
    start = max(1900, min(start, today.year - 11))
    rows, row = [], []
    for year in range(start, start + 12):
        row.append(button(str(year), f"{prefix}year_{year}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    navigation = []
    if start > 1900:
        navigation.append(button("⬅️", f"{prefix}nav_year_{start - 12}"))
    if start + 12 <= today.year:
        navigation.append(button("➡️", f"{prefix}nav_year_{start + 12}"))
    if navigation:
        rows.append(navigation)
    if with_unknown:
        rows.append([button(t(language, "btn_unknown_year"), f"{prefix}year_none")])
    return InlineKeyboardMarkup(rows)


def categories_keyboard(language, prefix=""):
    buttons = [button(label, f"{prefix}cat_{key}") for key, label in categories(language)]
    return InlineKeyboardMarkup([buttons[i:i + 2] for i in range(0, len(buttons), 2)])


def keypad_keyboard(language):
    return InlineKeyboardMarkup([
        [button("1", "num_1"), button("2", "num_2"), button("3", "num_3")],
        [button("4", "num_4"), button("5", "num_5"), button("6", "num_6")],
        [button("7", "num_7"), button("8", "num_8"), button("9", "num_9")],
        [button("+", "num_+"), button("0", "num_0"), button("⌫", "num_del")],
        [button(t(language, "btn_done"), "num_done"), button(t(language, "btn_skip"), "num_skip")],
    ])


def zones_keyboard(language):
    buttons = [button(label, f"tz_{tz}") for label, tz in zone_options(language)]
    return InlineKeyboardMarkup([buttons[i:i + 2] for i in range(0, len(buttons), 2)])


def languages_keyboard():
    return InlineKeyboardMarkup([[button(LANGUAGE_NAMES[code], f"lang_{code}") for code in SUPPORTED_LANGUAGES]])


def keypad_text(language, number):
    return t(language, "keypad_text", number=esc(number))


# --- /start, /help ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    language = lang_of(update)
    keyboard = [[button(t(language, "btn_add_birthday"), "start_new")], [button(t(language, "btn_view_birthdays"), "start_list")]]
    await update.message.reply_text(t(language, "start_greeting"), reply_markup=InlineKeyboardMarkup(keyboard))
    if not db.get_settings(update.effective_chat.id)['timezone_set']:
        await update.message.reply_text(t(language, "zone_prompt_start"), reply_markup=zones_keyboard(language))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t(lang_of(update), "help_text"), parse_mode="HTML")


async def stray_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t(lang_of(update), "stray_text"))


# --- CREATE A BIRTHDAY ---
async def new_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
    await update.effective_message.reply_text(t(lang_of(update), "new_ask_name"))
    return NAME


async def new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    language = lang_of(update)
    name = clean_name(update.message.text)
    if not name:
        await update.message.reply_text(t(language, "name_invalid"))
        return NAME
    context.user_data['name'] = name
    await update.message.reply_text(t(language, "name_saved", name=esc(name)), reply_markup=months_keyboard(language), parse_mode="HTML")
    return MONTH


async def receive_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    month = query.data.split('_')[1]
    context.user_data['month'] = month
    await edit(query, t(lang_of(update), "ask_day"), days_keyboard(month))
    return DAY


async def receive_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = lang_of(update)
    day_month = f"{query.data.split('_')[1]}/{context.user_data['month']}"
    context.user_data['day_month'] = day_month
    keyboard = [[button(t(language, "btn_yes_know"), "yes_year")], [button(t(language, "btn_no_skip"), "no_year")]]
    await edit(query, t(language, "ask_year", date=format_day_month(day_month, language)), InlineKeyboardMarkup(keyboard))
    return ASK_YEAR


async def ask_year_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = lang_of(update)
    if query.data == "yes_year":
        today = today_for_user(update.effective_chat.id)
        await edit(query, t(language, "pick_year"), years_keyboard(1990, today, language=language))
        return PICK_YEAR
    context.user_data['birth_year'] = ""
    return await show_category_keyboard(update)


async def navigate_years(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    today = today_for_user(update.effective_chat.id)
    await query.edit_message_reply_markup(reply_markup=years_keyboard(int(query.data.split('_')[2]), today))
    return PICK_YEAR


async def receive_year_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    year = query.data.split('_')[1]
    if not date_compatible_with_year(context.user_data['day_month'], year):
        await query.answer(t(lang_of(update), "year_leap_alert"), show_alert=True)
        return PICK_YEAR
    await query.answer()
    context.user_data['birth_year'] = year
    return await show_category_keyboard(update)


async def receive_year_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    language = lang_of(update)
    year = parse_year(update.message.text, today_for_user(update.effective_chat.id))
    if year is None:
        await update.message.reply_text(t(language, "year_invalid"))
        return PICK_YEAR
    if not date_compatible_with_year(context.user_data['day_month'], year):
        await update.message.reply_text(t(language, "year_leap_text"))
        return PICK_YEAR
    context.user_data['birth_year'] = str(year)
    return await show_category_keyboard(update)


async def show_category_keyboard(update: Update):
    language = lang_of(update)
    await reply(update, t(language, "ask_category"), categories_keyboard(language))
    return CATEGORY


async def receive_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = lang_of(update)
    context.user_data['category'] = query.data.split('_', 1)[1]
    keyboard = [[button(t(language, "btn_add_number"), "yes_phone")], [button(t(language, "btn_finish"), "no_phone")]]
    await edit(query, t(language, "ask_phone"), InlineKeyboardMarkup(keyboard))
    return ASK_PHONE


async def ask_phone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = lang_of(update)
    if query.data == "yes_phone":
        prefix = phone_prefix(db.get_settings(update.effective_chat.id)['timezone'])
        context.user_data['phone_draft'] = f"+{prefix}"
        await edit(query, keypad_text(language, context.user_data['phone_draft']), keypad_keyboard(language))
        return ENTER_PHONE
    context.user_data['phone'] = ""
    return await save_and_finish(update, context)


async def handle_phone_keypad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    language = lang_of(update)
    action = query.data.split('_')[1]
    current = context.user_data.get('phone_draft', '+')

    if action == "skip":
        await query.answer()
        context.user_data['phone'] = ""
        return await save_and_finish(update, context)
    if action == "done":
        phone = normalize_phone(current)
        if phone is None:
            await query.answer(t(language, "phone_incomplete"), show_alert=True)
            return ENTER_PHONE
        await query.answer()
        context.user_data['phone'] = phone
        return await save_and_finish(update, context)

    await query.answer()
    if action == "del":
        new = current[:-1]
    elif action == "+" and current:  # a '+' only makes sense at the start
        new = current
    else:
        new = current + action
    if len(new) > MAX_KEYPAD_PHONE:
        new = current
    context.user_data['phone_draft'] = new
    await edit(query, keypad_text(language, new), keypad_keyboard(language))
    return ENTER_PHONE


async def receive_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = normalize_phone(update.message.contact.phone_number)
    if phone is None:
        await update.message.reply_text(t(lang_of(update), "contact_invalid"))
        return ENTER_PHONE
    context.user_data['phone'] = phone
    return await save_and_finish(update, context)


async def receive_phone_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = normalize_phone(update.message.text)
    if phone is None:
        await update.message.reply_text(t(lang_of(update), "phone_invalid"))
        return ENTER_PHONE
    context.user_data['phone'] = phone
    return await save_and_finish(update, context)


async def save_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    language = lang_of(update)
    data = context.user_data
    db.add_birthday(update.effective_chat.id, data['name'], data['day_month'], data['birth_year'], data['category'], data['phone'])
    summary = t(language, "saved_summary", name=esc(data['name']), date=format_day_month(data['day_month'], language),
                category=esc(category_label(data['category'], language)))
    if year_known(data['birth_year']):
        summary += t(language, "saved_born", year=data['birth_year'])
    data.clear()
    await reply(update, summary, InlineKeyboardMarkup([[button(t(language, "btn_add_another"), "start_new")]]))
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(t(lang_of(update), "cancelled"))
    return ConversationHandler.END


# --- LIST ---
def filters_keyboard(language):
    return InlineKeyboardMarkup([
        [button(t(language, "btn_upcoming"), "list_upcoming")],
        [button(t(language, "btn_this_month"), "list_month")],
        [button(t(language, "btn_all"), "list_all")],
    ])


async def list_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    language = lang_of(update)
    await update.effective_message.reply_text(t(language, "list_ask"), reply_markup=filters_keyboard(language))


async def list_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = lang_of(update)
    await edit(query, t(language, "list_ask"), filters_keyboard(language))


def _list_label(birthday, today, language):
    _, name, day_month, birth_year, _, _ = birthday
    remaining = days_until(day_month, today)
    if remaining == 0:
        when = t(language, "label_today")
    elif remaining == 1:
        when = t(language, "label_tomorrow")
    else:
        when = t(language, "label_in_days", n=remaining)
    age = age_on(birth_year, next_birthday(day_month, today))
    extra = t(language, "label_age", n=age) if age else ""
    return f"{name} · {day_month}{extra} ({when})"


async def handle_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = lang_of(update)
    parts = query.data.split('_')
    filter_name = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 0

    chat_id = update.effective_chat.id
    birthdays = db.get_birthdays_by_user(chat_id)
    if not birthdays:
        return await edit(query, t(language, "list_none"))

    today = today_for_user(chat_id)
    ordered = sorted(birthdays, key=lambda b: days_until(b[2], today))
    if filter_name == "upcoming":
        filtered = [b for b in ordered if days_until(b[2], today) <= 30]
        title = t(language, "title_upcoming")
    elif filter_name == "month":
        filtered = [b for b in ordered if b[2].split('/')[1] == f"{today.month:02d}"]
        title = t(language, "title_month", month=month_name(today.month, language))
    else:
        filtered = ordered
        title = t(language, "title_all")

    back = button(t(language, "btn_back"), "list_back")
    if not filtered:
        return await edit(query, t(language, "list_empty_filter"), InlineKeyboardMarkup([[back]]))

    total_pages = (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(0, min(page, total_pages - 1))
    keyboard = [[button(_list_label(b, today, language), f"view_{b[0]}")] for b in filtered[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]]
    if total_pages > 1:
        navigation = []
        if page > 0:
            navigation.append(button("⬅️", f"list_{filter_name}_{page - 1}"))
        navigation.append(button(f"{page + 1}/{total_pages}", "noop"))
        if page < total_pages - 1:
            navigation.append(button("➡️", f"list_{filter_name}_{page + 1}"))
        keyboard.append(navigation)
    keyboard.append([back])
    await edit(query, f"{title}\n\n{t(language, 'list_hint')}", InlineKeyboardMarkup(keyboard))


async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()


def profile_text(birthday, today, language):
    _, _, name, day_month, birth_year, category, phone = birthday
    if year_known(birth_year):
        age = age_on(birth_year, next_birthday(day_month, today))
        year_line = t(language, "profile_year", year=birth_year) + (t(language, "profile_will_turn", age=age) if age else "")
    else:
        year_line = t(language, "profile_year_unknown")
    return t(language, "profile_text", name=esc(name), date=format_day_month(day_month, language), year_line=year_line,
             category=esc(category_label(category, language)),
             phone='+' + esc(phone) if phone else t(language, "profile_no_phone"))


def profile_keyboard(birthday_id, language):
    return InlineKeyboardMarkup([
        [button(t(language, "btn_edit"), f"edit_{birthday_id}"), button(t(language, "btn_delete"), f"delete_{birthday_id}")],
        [button(t(language, "btn_back_to_list"), "list_all")],
    ])


def _back_to_list(language):
    return InlineKeyboardMarkup([[button(t(language, "btn_back"), "list_all")]])


async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = lang_of(update)
    chat_id = update.effective_chat.id
    birthday = db.get_birthday(int(query.data.split('_')[1]), chat_id)
    if not birthday:
        return await edit(query, t(language, "profile_not_found"), _back_to_list(language))
    await edit(query, profile_text(birthday, today_for_user(chat_id), language), profile_keyboard(birthday[0], language))


async def delete_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for confirmation before deleting."""
    query = update.callback_query
    await query.answer()
    language = lang_of(update)
    birthday_id = int(query.data.split('_')[1])
    birthday = db.get_birthday(birthday_id, update.effective_chat.id)
    if not birthday:
        return await edit(query, t(language, "profile_not_found"), _back_to_list(language))
    keyboard = [[button(t(language, "btn_yes_delete"), f"confirm_delete_{birthday_id}"), button(t(language, "btn_no"), f"view_{birthday_id}")]]
    await edit(query, t(language, "confirm_delete", name=esc(birthday[2])), InlineKeyboardMarkup(keyboard))


async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = lang_of(update)
    deleted = db.delete_birthday(int(query.data.split('_')[2]), update.effective_chat.id)
    await edit(query, t(language, "deleted" if deleted else "already_gone"), _back_to_list(language))


# --- EDIT ---
async def _show_profile_after_edit(update, context, birthday_id):
    language = lang_of(update)
    birthday = db.get_birthday(birthday_id, update.effective_chat.id)
    context.user_data.clear()
    await reply(update, t(language, "changes_saved") + "\n\n" + profile_text(birthday, today_for_user(update.effective_chat.id), language),
                profile_keyboard(birthday_id, language))
    return ConversationHandler.END


async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = lang_of(update)
    birthday_id = int(query.data.split('_')[1])
    birthday = db.get_birthday(birthday_id, update.effective_chat.id)
    if not birthday:
        await edit(query, t(language, "profile_not_found"))
        return ConversationHandler.END
    context.user_data.clear()
    context.user_data['edit_id'] = birthday_id
    keyboard = [
        [button(t(language, "btn_field_name"), "efield_name"), button(t(language, "btn_field_date"), "efield_date")],
        [button(t(language, "btn_field_year"), "efield_year"), button(t(language, "btn_field_category"), "efield_category")],
        [button(t(language, "btn_field_phone"), "efield_phone")],
        [button(t(language, "btn_cancel"), "ecancel")],
    ]
    await edit(query, t(language, "edit_what", name=esc(birthday[2])), InlineKeyboardMarkup(keyboard))
    return E_MENU


async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = lang_of(update)
    birthday_id = context.user_data.get('edit_id')
    birthday = db.get_birthday(birthday_id, update.effective_chat.id) if birthday_id else None
    context.user_data.clear()
    if birthday:
        await edit(query, profile_text(birthday, today_for_user(update.effective_chat.id), language), profile_keyboard(birthday_id, language))
    else:
        await edit(query, t(language, "edit_cancelled"))
    return ConversationHandler.END


async def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = lang_of(update)
    field = query.data.split('_')[1]
    if field == "name":
        await edit(query, t(language, "edit_ask_name"))
        return E_NAME
    if field == "date":
        await edit(query, t(language, "edit_ask_month"), months_keyboard(language, "e"))
        return E_MONTH
    if field == "year":
        today = today_for_user(update.effective_chat.id)
        await edit(query, t(language, "edit_ask_year"), years_keyboard(1990, today, "e", with_unknown=True, language=language))
        return E_YEAR
    if field == "category":
        await edit(query, t(language, "edit_ask_category"), categories_keyboard(language, "e"))
        return E_CATEGORY
    await edit(query, t(language, "edit_ask_phone"), InlineKeyboardMarkup([[button(t(language, "btn_remove_phone"), "ephone_remove")]]))
    return E_PHONE


async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = clean_name(update.message.text)
    if not name:
        await update.message.reply_text(t(lang_of(update), "name_invalid"))
        return E_NAME
    birthday_id = context.user_data['edit_id']
    db.update_birthday(birthday_id, update.effective_chat.id, name=name)
    return await _show_profile_after_edit(update, context, birthday_id)


async def edit_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    month = query.data.split('_')[1]
    context.user_data['month'] = month
    await edit(query, t(lang_of(update), "ask_day"), days_keyboard(month, "e"))
    return E_DAY


async def edit_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    birthday_id = context.user_data['edit_id']
    day_month = f"{query.data.split('_')[1]}/{context.user_data['month']}"
    birthday = db.get_birthday(birthday_id, update.effective_chat.id)
    if not date_compatible_with_year(day_month, birthday[4]):
        await query.answer(t(lang_of(update), "edit_leap_alert", name=birthday[2], year=birthday[4]), show_alert=True)
        return E_DAY
    await query.answer()
    db.update_birthday(birthday_id, update.effective_chat.id, day_month=day_month)
    return await _show_profile_after_edit(update, context, birthday_id)


async def edit_navigate_years(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    today = today_for_user(update.effective_chat.id)
    await query.edit_message_reply_markup(
        reply_markup=years_keyboard(int(query.data.split('_')[3]), today, "e", with_unknown=True, language=lang_of(update)))
    return E_YEAR


async def _save_year(update, context, birth_year, report_error):
    birthday_id = context.user_data['edit_id']
    birthday = db.get_birthday(birthday_id, update.effective_chat.id)
    if not date_compatible_with_year(birthday[3], birth_year):
        await report_error(t(lang_of(update), "year_leap_alert"))
        return E_YEAR
    db.update_birthday(birthday_id, update.effective_chat.id, birth_year=str(birth_year))
    return await _show_profile_after_edit(update, context, birthday_id)


async def edit_year_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    value = query.data.split('_')[1]
    birth_year = "" if value == "none" else value

    async def report_error(text):
        await query.answer(text, show_alert=True)
    result = await _save_year(update, context, birth_year, report_error)
    if result == ConversationHandler.END:
        await query.answer()
    return result


async def edit_year_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    year = parse_year(update.message.text, today_for_user(update.effective_chat.id))
    if year is None:
        await update.message.reply_text(t(lang_of(update), "year_invalid"))
        return E_YEAR
    return await _save_year(update, context, year, update.message.reply_text)


async def edit_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    birthday_id = context.user_data['edit_id']
    db.update_birthday(birthday_id, update.effective_chat.id, category=query.data.split('_', 1)[1])
    return await _show_profile_after_edit(update, context, birthday_id)


async def _save_phone(update, context, phone):
    birthday_id = context.user_data['edit_id']
    db.update_birthday(birthday_id, update.effective_chat.id, phone=phone)
    return await _show_profile_after_edit(update, context, birthday_id)


async def edit_phone_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    return await _save_phone(update, context, "")


async def edit_phone_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = normalize_phone(update.message.text)
    if phone is None:
        await update.message.reply_text(t(lang_of(update), "phone_invalid"))
        return E_PHONE
    return await _save_phone(update, context, phone)


async def edit_phone_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = normalize_phone(update.message.contact.phone_number)
    if phone is None:
        await update.message.reply_text(t(lang_of(update), "contact_invalid"))
        return E_PHONE
    return await _save_phone(update, context, phone)


# --- SETTINGS ---
def settings_text(chat_id, language):
    settings = db.get_settings(chat_id)
    local_time = datetime.now(pytz.timezone(settings['timezone'])).strftime("%H:%M")
    return t(language, "settings_text", hour=settings['hour'], zone=esc(timezone_label(settings['timezone'], language)),
             time=local_time, language_name=LANGUAGE_NAMES[language])


def settings_keyboard(language):
    return InlineKeyboardMarkup([
        [button(t(language, "btn_change_hour"), "set_hour"), button(t(language, "btn_change_zone"), "set_zone")],
        [button(t(language, "btn_change_language"), "set_language")],
    ])


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    language = lang_of(update)
    await update.message.reply_text(settings_text(update.effective_chat.id, language), reply_markup=settings_keyboard(language), parse_mode="HTML")


async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = lang_of(update)
    await edit(query, settings_text(update.effective_chat.id, language), settings_keyboard(language))


async def choose_hour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = lang_of(update)
    buttons = [button(f"{h:02d}:00", f"hour_{h:02d}:00") for h in range(24)]
    rows = [buttons[i:i + 4] for i in range(0, 24, 4)]
    rows.append([button(t(language, "btn_back"), "settings_menu")])
    await edit(query, t(language, "choose_hour"), InlineKeyboardMarkup(rows))


async def choose_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = lang_of(update)
    await edit(query, t(language, "choose_zone"), zones_keyboard(language))


async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await edit(query, t(lang_of(update), "choose_language"), languages_keyboard())


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t(lang_of(update), "choose_language"), reply_markup=languages_keyboard())


async def save_language_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = query.data.split('_', 1)[1]
    if language not in SUPPORTED_LANGUAGES:
        return
    db.save_language(update.effective_chat.id, language)
    await edit(query, t(language, "language_saved"))


async def save_hour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = lang_of(update)
    hour = query.data.split('_')[1]
    db.save_alarm_hour(update.effective_chat.id, hour)
    timezone = db.get_settings(update.effective_chat.id)['timezone']
    await edit(query, t(language, "hour_saved", hour=hour, zone=esc(timezone_label(timezone, language))))


async def save_zone_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    language = lang_of(update)
    timezone = query.data.split('_', 1)[1]
    if not is_valid_timezone(timezone):
        return await edit(query, t(language, "zone_invalid"))
    db.save_timezone(update.effective_chat.id, timezone)
    hour = db.get_settings(update.effective_chat.id)['hour']
    await edit(query, t(language, "zone_saved", zone=esc(timezone_label(timezone, language)), hour=hour))


async def zone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    language = lang_of(update)
    if not context.args:
        return await update.message.reply_text(t(language, "zone_pick"), reply_markup=zones_keyboard(language))
    name = context.args[0]
    if not is_valid_timezone(name):
        return await update.message.reply_text(t(language, "zone_unknown"), parse_mode="HTML")
    db.save_timezone(update.effective_chat.id, name)
    await update.message.reply_text(t(language, "zone_cmd_saved", zone=name))


# --- EXPORT ---
def _safe_cell(value):
    """Stop spreadsheets from interpreting text as a formula."""
    text = str(value)
    return "'" + text if text[:1] in "=+-@" else text


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    language = lang_of(update)
    birthdays = db.get_birthdays_by_user(chat_id)
    if not birthdays:
        return await update.message.reply_text(t(language, "export_none"))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(t(language, "csv_headers"))
    for b in birthdays:
        writer.writerow([_safe_cell(b[1]), b[2], b[3], category_label(b[4], language), b[5]])
    await context.bot.send_document(chat_id=chat_id, document=output.getvalue().encode('utf-8-sig'),
                                    filename=t(language, "csv_filename"), caption=t(language, "export_caption"))


# --- GREETING MESSAGE ---
def build_greeting_message(birthday_id, name, birth_year, category, phone, previous_text="", today=None, language="es",
                           day_month=None):
    today = today or datetime.now().date()
    age = age_on(birth_year, today)
    text = t(language, "reminder_title") + t(language, "reminder_today", name=esc(name))
    text += t(language, "reminder_age", age=age) if age else t(language, "reminder_no_age")

    born = birth_date(birth_year, day_month) if day_month else None
    idea = pick_suggestion(category, name, age, previous_text, language, born, today)
    text += t(language, "reminder_suggestion", idea=esc(idea))
    encoded = urllib.parse.quote_plus(idea)

    first_row = []
    if len(idea) <= MAX_COPY_TEXT:
        first_row.append(InlineKeyboardButton(t(language, "btn_copy"), copy_text=CopyTextButton(text=idea)))
    first_row.append(button(t(language, "btn_another"), f"another_{birthday_id}"))
    if phone:
        share_row = [InlineKeyboardButton("🟢 WhatsApp", url=f"https://api.whatsapp.com/send?phone={phone}&text={encoded}"),
                     InlineKeyboardButton("🔵 Telegram", url=f"https://t.me/+{phone}?text={encoded}")]
    else:
        share_row = [InlineKeyboardButton("🟢 WhatsApp", url=f"https://api.whatsapp.com/send?text={encoded}"),
                     InlineKeyboardButton(t(language, "btn_share_tg"), url=f"https://t.me/share/url?url={encoded}")]
    return text, InlineKeyboardMarkup([first_row, share_row])


async def change_suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    language = lang_of(update)
    birthday = db.get_birthday(int(query.data.split('_')[1]), chat_id)
    if not birthday:
        return await query.answer(t(language, "birthday_gone"), show_alert=True)
    birthday_id, _, name, day_month, birth_year, category, phone = birthday
    text, keyboard = build_greeting_message(birthday_id, name, birth_year, category, phone,
                                            query.message.text or "", today_for_user(chat_id), language, day_month)
    await edit(query, text, keyboard)
    await query.answer()


# --- ERRORS ---
async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, NetworkError):
        # Telegram can't be reached right now: replying would fail too, so just note it and move on
        logger.warning("Network error while processing an update: %s", context.error)
        return
    logger.error("Error processing an update", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(t(lang_of(update), "error_generic"))
        except Exception:
            logger.exception("Could not tell the user about the error")


# --- REGISTRATION ---
def build_conversation():
    def cb(function, pattern):
        return CallbackQueryHandler(function, pattern=pattern)

    text = filters.TEXT & ~filters.COMMAND
    return ConversationHandler(
        entry_points=[CommandHandler(CMD_NEW, new_start), cb(new_start, r"^start_new$"), cb(edit_start, r"^edit_\d+$")],
        states={
            NAME: [MessageHandler(text, new_name)],
            MONTH: [cb(receive_month, r"^month_\d\d$")],
            DAY: [cb(receive_day, r"^day_\d\d$")],
            ASK_YEAR: [cb(ask_year_callback, r"^(yes_year|no_year)$")],
            PICK_YEAR: [cb(navigate_years, r"^nav_year_\d+$"), cb(receive_year_button, r"^year_\d{4}$"),
                        MessageHandler(text, receive_year_text)],
            CATEGORY: [cb(receive_category, rf"^cat_({CATEGORY_PATTERN})$")],
            ASK_PHONE: [cb(ask_phone_callback, r"^(yes_phone|no_phone)$")],
            ENTER_PHONE: [cb(handle_phone_keypad, r"^num_"), MessageHandler(filters.CONTACT, receive_contact),
                          MessageHandler(text, receive_phone_text)],
            E_MENU: [cb(edit_field, r"^efield_(name|date|year|category|phone)$"), cb(edit_cancel, r"^ecancel$")],
            E_NAME: [MessageHandler(text, edit_name)],
            E_MONTH: [cb(edit_month, r"^emonth_\d\d$")],
            E_DAY: [cb(edit_day, r"^eday_\d\d$")],
            E_YEAR: [cb(edit_navigate_years, r"^enav_year_\d+$"), cb(edit_year_button, r"^eyear_(\d{4}|none)$"),
                     MessageHandler(text, edit_year_text)],
            E_CATEGORY: [cb(edit_category, rf"^ecat_({CATEGORY_PATTERN})$")],
            E_PHONE: [cb(edit_phone_remove, r"^ephone_remove$"), MessageHandler(filters.CONTACT, edit_phone_contact),
                      MessageHandler(text, edit_phone_text)],
        },
        fallbacks=[CommandHandler(CMD_CANCEL, cancel)],
        allow_reentry=True,
    )


def register_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler(CMD_HELP, help_command))
    app.add_handler(CommandHandler(CMD_EXPORT, export_command))
    app.add_handler(CommandHandler(CMD_SETTINGS, settings_command))
    app.add_handler(CommandHandler(CMD_TIMEZONE, zone_command))
    app.add_handler(CommandHandler(CMD_LANGUAGE, language_command))
    app.add_handler(build_conversation())
    app.add_handler(CommandHandler(CMD_LIST, list_start))
    for function, pattern in [
        (list_start, r"^start_list$"),
        (list_back, r"^list_back$"),
        (handle_list, r"^list_(upcoming|month|all)(_\d+)?$"),
        (noop, r"^noop$"),
        (view_profile, r"^view_\d+$"),
        (delete_prompt, r"^delete_\d+$"),
        (confirm_delete, r"^confirm_delete_\d+$"),
        (change_suggestion, r"^another_\d+$"),
        (settings_menu, r"^settings_menu$"),
        (choose_hour, r"^set_hour$"),
        (choose_zone, r"^set_zone$"),
        (choose_language, r"^set_language$"),
        (save_language_button, r"^lang_[a-z]{2}$"),
        (save_hour, r"^hour_\d\d:00$"),
        (save_zone_button, r"^tz_"),
    ]:
        app.add_handler(CallbackQueryHandler(function, pattern=pattern))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, stray_text))
    app.add_error_handler(error_handler)
