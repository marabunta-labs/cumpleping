import sqlite3
from contextlib import closing

import pytest

import database as db


def with_language(settings, language='es', language_set=False):
    return {**settings, 'language': language, 'language_set': language_set}


def add(chat_id=1, name="Ana", day_month="05/03", birth_year="1990", category="friends", phone=""):
    db.add_birthday(chat_id, name, day_month, birth_year, category, phone)
    return db.get_birthdays_by_user(chat_id)[-1][0]


def test_add_and_get():
    id_ = add()
    assert db.get_birthday(id_) == (id_, 1, "Ana", "05/03", "1990", "friends", "")
    assert db.get_birthdays_by_user(1)[0][1] == "Ana"


def test_birthdays_are_isolated_per_user():
    add(chat_id=1)
    add(chat_id=2, name="Luis")
    assert [b[1] for b in db.get_birthdays_by_user(1)] == ["Ana"]
    assert [b[1] for b in db.get_birthdays_by_user(2)] == ["Luis"]


def test_get_birthday_respects_owner():
    id_ = add(chat_id=1)
    assert db.get_birthday(id_, chat_id=1) is not None
    assert db.get_birthday(id_, chat_id=2) is None


def test_get_birthdays_on_is_exact():
    add(day_month="05/03")
    add(name="Other", day_month="05/030")  # must not match by prefix
    assert [b[2] for b in db.get_birthdays_on("05/03")] == ["Ana"]


def test_get_all_birthdays():
    add(chat_id=1)
    add(chat_id=2)
    assert len(db.get_all_birthdays()) == 2


def test_update():
    id_ = add()
    assert db.update_birthday(id_, 1, name="Ana María", phone="34600111222")
    row = db.get_birthday(id_)
    assert row[2] == "Ana María" and row[6] == "34600111222"


def test_update_someone_elses_does_nothing():
    id_ = add(chat_id=1)
    assert not db.update_birthday(id_, 2, name="Hack")
    assert db.get_birthday(id_)[2] == "Ana"


def test_update_rejects_non_editable_fields():
    id_ = add()
    with pytest.raises(ValueError):
        db.update_birthday(id_, 1, id=99)
    with pytest.raises(ValueError):
        db.update_birthday(id_, 1)


def test_delete_respects_owner():
    id_ = add(chat_id=1)
    assert not db.delete_birthday(id_, chat_id=2)
    assert db.get_birthday(id_) is not None
    assert db.delete_birthday(id_, chat_id=1)
    assert db.get_birthday(id_) is None


def test_delete_also_clears_sent_notices():
    id_ = add()
    db.claim_notice(id_, "2026-03-05")
    db.delete_birthday(id_)
    assert db.claim_notice(id_, "2026-03-05")


def test_delete_by_name():
    add()
    assert db.delete_birthday_by_name(1, "Ana")
    assert not db.delete_birthday_by_name(1, "Ana")


def test_default_settings():
    assert db.get_settings(7) == with_language({'hour': '09:00', 'timezone': 'Europe/Madrid', 'timezone_set': False})


def test_hour_and_timezone_are_independent():
    db.save_alarm_hour(7, "18:00")
    db.save_timezone(7, "America/Mexico_City")
    assert db.get_settings(7) == with_language({'hour': '18:00', 'timezone': 'America/Mexico_City', 'timezone_set': True})
    db.save_alarm_hour(7, "10:00")
    assert db.get_settings(7)['timezone'] == 'America/Mexico_City'


def test_saving_timezone_without_previous_hour_keeps_default_hour():
    db.save_timezone(8, "America/Bogota")
    assert db.get_settings(8)['hour'] == "09:00"


def test_claim_notice_only_once():
    assert db.claim_notice(1, "2026-03-05")
    assert not db.claim_notice(1, "2026-03-05")
    assert db.claim_notice(1, "2027-03-05")
    db.release_notice(1, "2026-03-05")
    assert db.claim_notice(1, "2026-03-05")


def _make_legacy_db(path):
    """Database exactly as created by the Spanish-schema versions of the bot."""
    with closing(sqlite3.connect(path)) as con:
        con.execute("""CREATE TABLE cumpleaños (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, nombre TEXT,
                       fecha TEXT, anio TEXT, categoria TEXT, telefono TEXT)""")
        con.execute("CREATE TABLE preferencias (chat_id INTEGER PRIMARY KEY, hora_alarma TEXT)")
        con.execute("INSERT INTO cumpleaños (chat_id, nombre, fecha, anio, categoria, telefono) VALUES "
                    "(1, 'Ana', '05/03', '1990', 'Familia', '34600111222'), "
                    "(1, 'Luis', '10/11', 'Desconocido', 'Ninguna', ''), "
                    "(2, 'Eva', '01/01', '2000', 'Trabajo', '')")
        con.execute("INSERT INTO preferencias VALUES (5, '12:00')")
        con.commit()


def test_migration_of_legacy_spanish_database(tmp_path, monkeypatch):
    path = str(tmp_path / "legacy.db")
    _make_legacy_db(path)
    monkeypatch.setattr(db, "DB_PATH", path)
    db.create_database()
    db.create_database()  # idempotent
    assert db.get_birthdays_by_user(1) == [(1, "Ana", "05/03", "1990", "family", "34600111222"),
                                           (2, "Luis", "10/11", "", "none", "")]
    assert db.get_birthdays_by_user(2)[0][4] == "work"
    assert db.get_settings(5) == with_language({'hour': '12:00', 'timezone': 'Europe/Madrid', 'timezone_set': False})
    add(chat_id=1, name="Nueva")  # the migrated database is fully usable
    assert db.get_birthdays_by_user(1)[-1][1] == "Nueva"


def test_migration_of_legacy_preferences_with_timezone(tmp_path, monkeypatch):
    path = str(tmp_path / "legacy2.db")
    with closing(sqlite3.connect(path)) as con:
        con.execute("CREATE TABLE preferencias (chat_id INTEGER PRIMARY KEY, hora_alarma TEXT, zona_horaria TEXT)")
        con.execute("INSERT INTO preferencias VALUES (5, '12:00', 'America/Bogota')")
        con.execute("CREATE TABLE avisos_enviados (cumple_id INTEGER, fecha TEXT, PRIMARY KEY (cumple_id, fecha))")
        con.execute("INSERT INTO avisos_enviados VALUES (1, '2026-03-05')")
        con.commit()
    monkeypatch.setattr(db, "DB_PATH", path)
    db.create_database()
    assert db.get_settings(5) == with_language({'hour': '12:00', 'timezone': 'America/Bogota', 'timezone_set': True})
    assert not db.claim_notice(1, "2026-03-05")  # previous notices are preserved


def test_language_defaults_saves_and_keeps_other_settings():
    assert db.get_settings(9)['language'] == 'es' and not db.get_settings(9)['language_set']
    db.save_timezone(9, "America/Bogota")
    db.save_alarm_hour(9, "18:00")
    db.save_language(9, "en")
    settings = db.get_settings(9)
    assert settings['language'] == 'en' and settings['language_set']
    assert settings['timezone'] == "America/Bogota" and settings['hour'] == "18:00"
    db.save_timezone(9, "Europe/Madrid")
    assert db.get_settings(9)['language'] == 'en'  # changing the zone doesn't reset the language


def test_saving_language_first_does_not_mark_the_timezone_as_set():
    db.save_language(10, "en")
    assert not db.get_settings(10)['timezone_set']


def test_migration_adds_language_column_to_a_database_without_it(tmp_path, monkeypatch):
    path = str(tmp_path / "nolang.db")
    with closing(sqlite3.connect(path)) as con:
        con.execute("CREATE TABLE preferences (chat_id INTEGER PRIMARY KEY, alarm_hour TEXT, timezone TEXT)")
        con.execute("INSERT INTO preferences VALUES (5, '12:00', 'America/Bogota')")
        con.commit()
    monkeypatch.setattr(db, "DB_PATH", path)
    db.create_database()
    assert db.get_settings(5) == with_language({'hour': '12:00', 'timezone': 'America/Bogota', 'timezone_set': True})
