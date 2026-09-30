from datetime import date

import pytest
from telegram.error import BadRequest
from telegram.ext import Application, CallbackQueryHandler, ConversationHandler

import database as db
import handlers as h
from categories import CATEGORY_KEYS
from conftest import edited_keyboard, edited_text, keyboard_data, make_context, make_update, run

TODAY = date(2026, 6, 15)


@pytest.fixture(autouse=True)
def fixed_date(monkeypatch):
    monkeypatch.setattr(h, "today_for_user", lambda chat_id: TODAY)


def add(chat_id=1, name="Ana", day_month="20/06", birth_year="1990", category="friends", phone=""):
    db.add_birthday(chat_id, name, day_month, birth_year, category, phone)
    return db.get_birthdays_by_user(chat_id)[-1][0]


# ---------- create ----------
def test_full_creation_flow():
    ctx = make_context()
    assert run(h.new_start(make_update(text="/nuevo"), ctx)) == h.NAME
    assert run(h.new_name(make_update(text="  Ana   Pérez "), ctx)) == h.MONTH
    assert run(h.receive_month(make_update(data="month_03"), ctx)) == h.DAY
    assert run(h.receive_day(make_update(data="day_05"), ctx)) == h.ASK_YEAR
    assert run(h.ask_year_callback(make_update(data="yes_year"), ctx)) == h.PICK_YEAR
    assert run(h.receive_year_button(make_update(data="year_1995"), ctx)) == h.CATEGORY
    assert run(h.receive_category(make_update(data="cat_partner"), ctx)) == h.ASK_PHONE
    assert run(h.ask_phone_callback(make_update(data="no_phone"), ctx)) == ConversationHandler.END
    (row,) = db.get_birthdays_by_user(1)
    assert row[1:] == ("Ana Pérez", "05/03", "1995", "partner", "")


@pytest.mark.parametrize("category", CATEGORY_KEYS)
def test_every_category_can_be_saved(category):
    ctx = make_context({'name': 'Ana', 'day_month': '05/03', 'birth_year': ''})
    run(h.receive_category(make_update(data=f"cat_{category}"), ctx))
    run(h.ask_phone_callback(make_update(data="no_phone"), ctx))
    assert db.get_birthdays_by_user(1)[0][4] == category


def test_creation_without_year_stores_empty_year():
    ctx = make_context({'name': 'Ana', 'day_month': '05/03'})
    assert run(h.ask_year_callback(make_update(data="no_year"), ctx)) == h.CATEGORY
    assert ctx.user_data['birth_year'] == ""


def test_empty_or_long_name_is_rejected():
    ctx = make_context()
    update = make_update(text="x" * 80)
    assert run(h.new_name(update, ctx)) == h.NAME
    update.message.reply_text.assert_awaited_once()


def test_html_characters_in_name_are_escaped():
    update = make_update(text="<b>Ana_*")
    run(h.new_name(update, make_context()))
    assert "&lt;b&gt;Ana_*" in update.message.reply_text.call_args.args[0]


def test_february_has_29_days_and_april_30():
    update = make_update(data="month_02")
    run(h.receive_month(update, make_context()))
    assert "day_29" in keyboard_data(edited_keyboard(update))
    update = make_update(data="month_04")
    run(h.receive_month(update, make_context()))
    data = keyboard_data(edited_keyboard(update))
    assert "day_30" in data and "day_31" not in data


def test_typed_year_valid_and_invalid():
    ctx = make_context({'day_month': '05/03'})
    assert run(h.receive_year_text(make_update(text="abc"), ctx)) == h.PICK_YEAR
    assert run(h.receive_year_text(make_update(text="2030"), ctx)) == h.PICK_YEAR
    assert run(h.receive_year_text(make_update(text="1988"), ctx)) == h.CATEGORY
    assert ctx.user_data['birth_year'] == "1988"


def test_feb_29_rejects_non_leap_birth_year():
    ctx = make_context({'day_month': '29/02'})
    update = make_update(data="year_2001")
    assert run(h.receive_year_button(update, ctx)) == h.PICK_YEAR
    assert update.callback_query.answer.call_args.kwargs.get("show_alert")
    assert run(h.receive_year_text(make_update(text="2001"), ctx)) == h.PICK_YEAR
    assert run(h.receive_year_text(make_update(text="2000"), ctx)) == h.CATEGORY


def test_years_keyboard_limits():
    data = keyboard_data(h.years_keyboard(1990, TODAY))
    assert "nav_year_1978" in data and "nav_year_2002" in data
    data = keyboard_data(h.years_keyboard(5000, TODAY))  # clamped so future years are not offered
    assert "year_2026" in data and "year_2027" not in data
    assert not any(d.startswith("nav_year_") and int(d.split("_")[2]) > 2026 for d in data)
    data = keyboard_data(h.years_keyboard(0, TODAY))
    assert "year_1900" in data and not any(d.startswith("nav_year_") and int(d.split("_")[2]) < 1900 for d in data)


def test_phone_prefix_follows_the_time_zone():
    db.save_timezone(1, "America/Mexico_City")
    ctx = make_context()
    run(h.ask_phone_callback(make_update(data="yes_phone"), ctx))
    assert ctx.user_data['phone_draft'] == "+52"


def test_phone_prefix_defaults_to_spain():
    ctx = make_context()
    run(h.ask_phone_callback(make_update(data="yes_phone"), ctx))
    assert ctx.user_data['phone_draft'] == "+34"


def test_keypad_keys_delete_and_length_limit():
    ctx = make_context({'phone_draft': '+34'})
    for key in ["6", "0", "del", "0", "+"]:
        run(h.handle_phone_keypad(make_update(data=f"num_{key}"), ctx))
    assert ctx.user_data['phone_draft'] == "+3460"  # the '+' in the middle is ignored
    ctx.user_data['phone_draft'] = "+" + "1" * 15
    run(h.handle_phone_keypad(make_update(data="num_2"), ctx))
    assert len(ctx.user_data['phone_draft']) == 16


def test_keypad_done_with_incomplete_number_does_not_save():
    ctx = make_context({'phone_draft': '+34'})
    update = make_update(data="num_done")
    assert run(h.handle_phone_keypad(update, ctx)) == h.ENTER_PHONE
    assert update.callback_query.answer.call_args.kwargs.get("show_alert")
    assert db.get_birthdays_by_user(1) == []


def test_keypad_done_saves_normalized_phone():
    ctx = make_context({'name': 'Ana', 'day_month': '05/03', 'birth_year': '', 'category': 'friends',
                        'phone_draft': '+34600111222'})
    assert run(h.handle_phone_keypad(make_update(data="num_done"), ctx)) == ConversationHandler.END
    assert db.get_birthdays_by_user(1)[0][5] == "34600111222"


def test_keypad_skip_saves_without_phone():
    ctx = make_context({'name': 'Ana', 'day_month': '05/03', 'birth_year': '1990', 'category': 'friends', 'phone_draft': '+34'})
    assert run(h.handle_phone_keypad(make_update(data="num_skip"), ctx)) == ConversationHandler.END
    assert db.get_birthdays_by_user(1)[0][5] == ""


def test_invalid_typed_phone_and_contact_are_rejected():
    ctx = make_context()
    assert run(h.receive_phone_text(make_update(text="hola"), ctx)) == h.ENTER_PHONE
    assert run(h.receive_contact(make_update(contact="12"), ctx)) == h.ENTER_PHONE


def test_valid_typed_phone_saves():
    ctx = make_context({'name': 'Ana', 'day_month': '05/03', 'birth_year': '1990', 'category': 'friends'})
    assert run(h.receive_phone_text(make_update(text="+34 600-111-222"), ctx)) == ConversationHandler.END
    assert db.get_birthdays_by_user(1)[0][5] == "34600111222"


def test_cancel_clears_data():
    ctx = make_context({'name': 'Ana'})
    assert run(h.cancel(make_update(text="/cancelar"), ctx)) == ConversationHandler.END
    assert ctx.user_data == {}


# ---------- list ----------
def test_list_without_birthdays():
    update = make_update(data="list_all")
    run(h.handle_list(update, make_context()))
    assert "No tienes cumpleaños" in edited_text(update)


def test_list_orders_by_proximity_and_filters():
    add(name="Far", day_month="01/01")
    add(name="Near", day_month="20/06")
    add(name="Today", day_month="15/06")
    add(name="NextMonth", day_month="10/07")
    update = make_update(data="list_all")
    run(h.handle_list(update, make_context()))
    labels = [b.text for row in edited_keyboard(update).inline_keyboard for b in row]
    assert [label.split(" · ")[0] for label in labels[:4]] == ["Today", "Near", "NextMonth", "Far"]
    assert "¡ES HOY!" in labels[0]

    update = make_update(data="list_upcoming")
    run(h.handle_list(update, make_context()))
    assert "Far" not in str(update.callback_query.edit_message_text.call_args)

    update = make_update(data="list_month")
    run(h.handle_list(update, make_context()))
    text = str(update.callback_query.edit_message_text.call_args)
    assert "Near" in text and "Today" in text and "NextMonth" not in text


def test_list_shows_the_age_they_turn():
    add(name="Ana", day_month="20/06", birth_year="1990")
    update = make_update(data="list_all")
    run(h.handle_list(update, make_context()))
    assert "36 años" in str(update.callback_query.edit_message_text.call_args)


def test_list_pagination():
    for i in range(20):
        add(name=f"P{i:02d}", day_month="20/06")
    update = make_update(data="list_all")
    run(h.handle_list(update, make_context()))
    data = keyboard_data(edited_keyboard(update))
    assert sum(d.startswith("view_") for d in data) == h.PAGE_SIZE
    assert "list_all_1" in data
    update = make_update(data="list_all_2")
    run(h.handle_list(update, make_context()))
    data = keyboard_data(edited_keyboard(update))
    assert sum(d.startswith("view_") for d in data) == 4
    assert "list_all_1" in data and "list_all_3" not in data


def test_list_feb_29_does_not_crash():
    add(name="Leap", day_month="29/02", birth_year="2000")
    update = make_update(data="list_all")
    run(h.handle_list(update, make_context()))
    assert "Leap" in str(update.callback_query.edit_message_text.call_args)


def test_profile_shows_data_and_buttons():
    id_ = add(name="Ana_*", phone="34600111222", category="sports")
    update = make_update(data=f"view_{id_}")
    run(h.view_profile(update, make_context()))
    text = edited_text(update)
    assert "Ana_*" in text and "+34600111222" in text and "cumplirá 36" in text and "Deporte" in text
    data = keyboard_data(edited_keyboard(update))
    assert f"edit_{id_}" in data and f"delete_{id_}" in data


def test_profile_of_legacy_category_falls_back():
    id_ = add(category="Rara")
    update = make_update(data=f"view_{id_}")
    run(h.view_profile(update, make_context()))
    assert "Ninguna" in edited_text(update)


def test_cannot_view_or_delete_someone_elses_birthday():
    id_ = add(chat_id=1)
    update = make_update(chat_id=2, data=f"view_{id_}")
    run(h.view_profile(update, make_context()))
    assert "no encontrado" in edited_text(update)
    run(h.confirm_delete(make_update(chat_id=2, data=f"confirm_delete_{id_}"), make_context()))
    assert db.get_birthday(id_) is not None


def test_delete_asks_for_confirmation_then_deletes():
    id_ = add()
    update = make_update(data=f"delete_{id_}")
    run(h.delete_prompt(update, make_context()))
    assert db.get_birthday(id_) is not None
    assert f"confirm_delete_{id_}" in keyboard_data(edited_keyboard(update))
    run(h.confirm_delete(make_update(data=f"confirm_delete_{id_}"), make_context()))
    assert db.get_birthday(id_) is None


# ---------- edit ----------
def start_edit(id_, chat_id=1):
    ctx = make_context()
    state = run(h.edit_start(make_update(chat_id=chat_id, data=f"edit_{id_}"), ctx))
    return ctx, state


def test_edit_of_someone_elses_birthday_ends():
    id_ = add(chat_id=1)
    _, state = start_edit(id_, chat_id=2)
    assert state == ConversationHandler.END


def test_edit_name():
    id_ = add()
    ctx, state = start_edit(id_)
    assert state == h.E_MENU
    assert run(h.edit_field(make_update(data="efield_name"), ctx)) == h.E_NAME
    assert run(h.edit_name(make_update(text=""), ctx)) == h.E_NAME
    assert run(h.edit_name(make_update(text="Ana Nueva"), ctx)) == ConversationHandler.END
    assert db.get_birthday(id_)[2] == "Ana Nueva"
    assert ctx.user_data == {}


def test_edit_date():
    id_ = add(day_month="20/06")
    ctx, _ = start_edit(id_)
    assert run(h.edit_field(make_update(data="efield_date"), ctx)) == h.E_MONTH
    assert run(h.edit_month(make_update(data="emonth_12"), ctx)) == h.E_DAY
    assert run(h.edit_day(make_update(data="eday_25"), ctx)) == ConversationHandler.END
    assert db.get_birthday(id_)[3] == "25/12"


def test_edit_date_to_feb_29_with_non_leap_year_is_rejected():
    id_ = add(birth_year="2001")
    ctx, _ = start_edit(id_)
    run(h.edit_month(make_update(data="emonth_02"), ctx))
    assert run(h.edit_day(make_update(data="eday_29"), ctx)) == h.E_DAY
    assert db.get_birthday(id_)[3] == "20/06"


def test_edit_year_button_text_and_unknown():
    id_ = add(birth_year="1990")
    ctx, _ = start_edit(id_)
    assert run(h.edit_field(make_update(data="efield_year"), ctx)) == h.E_YEAR
    assert run(h.edit_year_text(make_update(text="zzz"), ctx)) == h.E_YEAR
    assert run(h.edit_year_text(make_update(text="1985"), ctx)) == ConversationHandler.END
    assert db.get_birthday(id_)[4] == "1985"

    ctx, _ = start_edit(id_)
    assert run(h.edit_year_button(make_update(data="eyear_none"), ctx)) == ConversationHandler.END
    assert db.get_birthday(id_)[4] == ""

    ctx, _ = start_edit(id_)
    assert run(h.edit_year_button(make_update(data="eyear_2001"), ctx)) == ConversationHandler.END
    assert db.get_birthday(id_)[4] == "2001"


def test_edit_year_incompatible_with_feb_29():
    id_ = add(day_month="29/02", birth_year="2000")
    ctx, _ = start_edit(id_)
    assert run(h.edit_year_button(make_update(data="eyear_2001"), ctx)) == h.E_YEAR
    assert db.get_birthday(id_)[4] == "2000"


@pytest.mark.parametrize("category", CATEGORY_KEYS)
def test_edit_category(category):
    id_ = add(category="friends")
    ctx, _ = start_edit(id_)
    assert run(h.edit_category(make_update(data=f"ecat_{category}"), ctx)) == ConversationHandler.END
    assert db.get_birthday(id_)[5] == category


def test_edit_phone_text_contact_and_remove():
    id_ = add(phone="1")
    ctx, _ = start_edit(id_)
    assert run(h.edit_phone_text(make_update(text="bad"), ctx)) == h.E_PHONE
    assert run(h.edit_phone_text(make_update(text="+52 55 1234 5678"), ctx)) == ConversationHandler.END
    assert db.get_birthday(id_)[6] == "525512345678"

    ctx, _ = start_edit(id_)
    assert run(h.edit_phone_contact(make_update(contact="+34600111222"), ctx)) == ConversationHandler.END
    assert db.get_birthday(id_)[6] == "34600111222"

    ctx, _ = start_edit(id_)
    assert run(h.edit_phone_remove(make_update(data="ephone_remove"), ctx)) == ConversationHandler.END
    assert db.get_birthday(id_)[6] == ""


def test_edit_cancel_changes_nothing():
    id_ = add()
    ctx, _ = start_edit(id_)
    assert run(h.edit_cancel(make_update(data="ecancel"), ctx)) == ConversationHandler.END
    assert db.get_birthday(id_)[2] == "Ana"


# ---------- settings ----------
def test_settings_show_hour_and_zone():
    db.save_timezone(1, "America/Mexico_City")
    update = make_update(text="/ajustes")
    run(h.settings_command(update, make_context()))
    text = update.message.reply_text.call_args.args[0]
    assert "09:00" in text and "México" in text


def test_hour_picker_offers_24_hours():
    update = make_update(data="set_hour")
    run(h.choose_hour(update, make_context()))
    hours = [d for d in keyboard_data(edited_keyboard(update)) if d.startswith("hour_")]
    assert hours == [f"hour_{i:02d}:00" for i in range(24)]


def test_save_hour():
    run(h.save_hour(make_update(data="hour_21:00"), make_context()))
    assert db.get_settings(1)['hour'] == "21:00"


def test_save_zone_from_button():
    run(h.save_zone_button(make_update(data="tz_America/Argentina/Buenos_Aires"), make_context()))
    assert db.get_settings(1)['timezone'] == "America/Argentina/Buenos_Aires"


def test_invalid_zone_is_not_saved():
    run(h.save_zone_button(make_update(data="tz_Marte/Base"), make_context()))
    assert not db.get_settings(1)['timezone_set']


def test_zone_command():
    update = make_update(text="/zona")
    run(h.zone_command(update, make_context()))
    assert update.message.reply_text.call_args.kwargs.get("reply_markup")
    run(h.zone_command(make_update(text="/zona"), make_context(args=["Asia/Tokyo"])))
    assert db.get_settings(1)['timezone'] == "Asia/Tokyo"
    update = make_update(text="/zona")
    run(h.zone_command(update, make_context(args=["Nada/Nada"])))
    assert db.get_settings(1)['timezone'] == "Asia/Tokyo"
    assert "No conozco" in update.message.reply_text.call_args.args[0]


def test_start_asks_for_zone_only_the_first_time():
    update = make_update(text="/start")
    run(h.start(update, make_context()))
    assert update.message.reply_text.await_count == 2
    db.save_timezone(1, "Europe/Madrid")
    update = make_update(text="/start")
    run(h.start(update, make_context()))
    assert update.message.reply_text.await_count == 1


# ---------- export ----------
def test_export_empty():
    update = make_update(text="/exportar")
    run(h.export_command(update, make_context()))
    assert "No tienes" in update.message.reply_text.call_args.args[0]


def test_export_csv_neutralizes_formulas_and_uses_labels():
    add(name="=CMD()", day_month="05/03", category="partner")
    ctx = make_context()
    run(h.export_command(make_update(text="/exportar"), ctx))
    content = ctx.bot.send_document.call_args.kwargs["document"].decode("utf-8-sig")
    assert "'=CMD()" in content and "Nombre,Fecha" in content and "Pareja" in content


# ---------- greeting message ----------
def test_message_includes_name_and_age():
    text, _ = h.build_greeting_message(1, "Ana", "1990", "friends", "", today=TODAY)
    assert "Ana" in text and "(36 años)" in text


def test_message_without_year_does_not_mention_age():
    text, _ = h.build_greeting_message(1, "Ana", "", "friends", "", today=TODAY)
    assert "años)" not in text


def test_message_escapes_html_in_name():
    text, _ = h.build_greeting_message(1, "<i>Ana_", "1990", "friends", "", today=TODAY)
    assert "<i>Ana_" not in text and "&lt;i&gt;Ana_" in text


@pytest.mark.parametrize("category", CATEGORY_KEYS)
def test_every_category_produces_a_suggestion_and_buttons(category):
    text, keyboard = h.build_greeting_message(1, "Ana", "1990", category, "", today=TODAY)
    assert "Sugerencia" in text
    assert "another_1" in keyboard_data(keyboard)


def test_age_fact_can_appear_in_the_suggestion():
    texts = {h.build_greeting_message(1, "Ana", "1996", "friends", "", today=TODAY)[0] for _ in range(200)}  # 30 years
    assert any("Bluey" in t for t in texts)


def test_copy_button_is_omitted_when_text_is_too_long():
    _, keyboard = h.build_greeting_message(1, "N" * 50, "1990", "family", "", today=TODAY)
    assert all(len(b.copy_text.text) <= 256 for row in keyboard.inline_keyboard for b in row if b.copy_text)


def test_buttons_with_phone():
    _, keyboard = h.build_greeting_message(1, "Ana", "1990", "friends", "34600111222", today=TODAY)
    urls = keyboard_data(keyboard)
    assert any("phone=34600111222" in u for u in urls if u)
    assert any("t.me/+34600111222" in u for u in urls if u)


def test_buttons_without_phone_share():
    _, keyboard = h.build_greeting_message(1, "Ana", "1990", "friends", "", today=TODAY)
    urls = keyboard_data(keyboard)
    assert any("whatsapp.com/send?text=" in u for u in urls if u)
    assert not any("phone=" in u for u in urls if u)


def test_change_suggestion_generates_another_message():
    id_ = add(name="Ana", birth_year="1990", category="family")
    text, _ = h.build_greeting_message(id_, "Ana", "1990", "family", "", today=TODAY)
    update = make_update(data=f"another_{id_}")
    update.callback_query.message.text = text
    run(h.change_suggestion(update, make_context()))
    new = edited_text(update)
    assert new != text and "Ana" in new


def test_change_suggestion_of_someone_elses_birthday():
    id_ = add(chat_id=1)
    update = make_update(chat_id=2, data=f"another_{id_}")
    run(h.change_suggestion(update, make_context()))
    update.callback_query.edit_message_text.assert_not_awaited()


def test_edit_ignores_message_not_modified():
    update = make_update(data="x")
    update.callback_query.edit_message_text.side_effect = BadRequest("Message is not modified")
    run(h.edit(update.callback_query, "hola"))
    update.callback_query.edit_message_text.side_effect = BadRequest("something else")
    with pytest.raises(BadRequest):
        run(h.edit(update.callback_query, "hola"))


# ---------- registration ----------
def _build_app():
    async def build():
        application = Application.builder().token("123:TEST").build()
        h.register_handlers(application)
        return application
    return run(build())


def _callback_patterns(application):
    patterns = []
    for group in application.handlers.values():
        for handler in group:
            if isinstance(handler, ConversationHandler):
                inner = list(handler.entry_points) + [x for handlers in handler.states.values() for x in handlers]
                patterns += [x.pattern for x in inner if isinstance(x, CallbackQueryHandler)]
            elif isinstance(handler, CallbackQueryHandler):
                patterns.append(handler.pattern)
    return patterns


def test_register_handlers_does_not_fail():
    assert _build_app().handlers[0]


def test_every_button_has_a_handler():
    """Each callback_data produced by the keyboards must match some registered handler."""
    patterns = _callback_patterns(_build_app())
    data = []
    for prefix in ("", "e"):
        data += keyboard_data(h.months_keyboard('es', prefix)) + keyboard_data(h.days_keyboard("02", prefix))
        data += keyboard_data(h.years_keyboard(1990, TODAY, prefix, with_unknown=bool(prefix)))
        data += keyboard_data(h.categories_keyboard('es', prefix))
    data += keyboard_data(h.keypad_keyboard('es')) + keyboard_data(h.zones_keyboard('es')) + keyboard_data(h.filters_keyboard('es'))
    data += keyboard_data(h.profile_keyboard(3, 'es')) + keyboard_data(h.settings_keyboard('es'))
    data += ["start_new", "start_list", "yes_year", "no_year", "yes_phone", "no_phone", "list_back", "noop",
             "confirm_delete_3", "view_3", "another_3", "settings_menu", "hour_09:00", "efield_name", "efield_date",
             "efield_year", "efield_category", "efield_phone", "ecancel", "ephone_remove", "list_all_2", "eyear_none",
             "set_language", "lang_en", "lang_es"]
    assert [d for d in data if not any(p.match(d) for p in patterns)] == []
