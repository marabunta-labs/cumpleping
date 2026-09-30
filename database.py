import os
import sqlite3
from contextlib import closing

from categories import LEGACY_CATEGORIES
from i18n import DEFAULT_LANGUAGE
from zones import DEFAULT_TIMEZONE

# Folder of this file (works the same locally and in the cloud). Can be overridden with CUMPLEPING_DB.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("CUMPLEPING_DB") or os.path.join(BASE_DIR, 'cumpleping.db')

DEFAULT_HOUR = "09:00"

_BIRTHDAY_COLUMNS = "id, chat_id, name, day_month, birth_year, category, phone"
EDITABLE_FIELDS = ("name", "day_month", "birth_year", "category", "phone")

# Column renames of the Spanish schema used by earlier versions
_LEGACY_BIRTHDAY_COLUMNS = {"nombre": "name", "fecha": "day_month", "anio": "birth_year",
                            "categoria": "category", "telefono": "phone"}
_LEGACY_PREFERENCE_COLUMNS = {"hora_alarma": "alarm_hour", "zona_horaria": "timezone"}
_LEGACY_UNKNOWN_YEAR = "Desconocido"


def get_connection():
    return sqlite3.connect(DB_PATH)


def _execute(sql, params=(), fetch=None):
    """Run one statement and close the connection. fetch: None, 'one' or 'all'. Returns (result, rowcount)."""
    with closing(get_connection()) as connection:
        cursor = connection.execute(sql, params)
        result = None
        if fetch == 'one':
            result = cursor.fetchone()
        elif fetch == 'all':
            result = cursor.fetchall()
        connection.commit()
        return result, cursor.rowcount


def _tables(connection):
    return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def _columns(connection, table):
    return [row[1] for row in connection.execute(f'PRAGMA table_info({table})')]


def _migrate_legacy_schema(connection):
    """Upgrade databases created by earlier versions (Spanish table and column names)."""
    tables = _tables(connection)
    if 'cumpleaños' in tables and 'birthdays' not in tables:
        connection.execute('ALTER TABLE "cumpleaños" RENAME TO birthdays')
        for old, new in _LEGACY_BIRTHDAY_COLUMNS.items():
            connection.execute(f'ALTER TABLE birthdays RENAME COLUMN {old} TO {new}')
    if 'preferencias' in tables and 'preferences' not in tables:
        connection.execute('ALTER TABLE preferencias RENAME TO preferences')
        if 'zona_horaria' not in _columns(connection, 'preferences'):
            connection.execute('ALTER TABLE preferences ADD COLUMN zona_horaria TEXT')
        for old, new in _LEGACY_PREFERENCE_COLUMNS.items():
            connection.execute(f'ALTER TABLE preferences RENAME COLUMN {old} TO {new}')
    if 'avisos_enviados' in tables and 'sent_notices' not in tables:
        connection.execute('ALTER TABLE avisos_enviados RENAME TO sent_notices')
        connection.execute('ALTER TABLE sent_notices RENAME COLUMN cumple_id TO birthday_id')
        connection.execute('ALTER TABLE sent_notices RENAME COLUMN fecha TO date')


def _migrate_legacy_values(connection):
    """Spanish category names -> category keys; 'Desconocido' -> empty birth year."""
    for old, new in LEGACY_CATEGORIES.items():
        connection.execute('UPDATE birthdays SET category = ? WHERE category = ?', (new, old))
    connection.execute("UPDATE birthdays SET birth_year = '' WHERE birth_year = ? OR birth_year IS NULL",
                       (_LEGACY_UNKNOWN_YEAR,))


def create_database():
    with closing(get_connection()) as connection:
        _migrate_legacy_schema(connection)
        connection.execute('''
            CREATE TABLE IF NOT EXISTS birthdays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                name TEXT,
                day_month TEXT,
                birth_year TEXT,
                category TEXT,
                phone TEXT
            )
        ''')
        connection.execute('CREATE INDEX IF NOT EXISTS idx_birthdays_chat ON birthdays (chat_id)')
        connection.execute('''
            CREATE TABLE IF NOT EXISTS preferences (
                chat_id INTEGER PRIMARY KEY,
                alarm_hour TEXT,
                timezone TEXT,
                language TEXT
            )
        ''')
        if 'language' not in _columns(connection, 'preferences'):
            connection.execute('ALTER TABLE preferences ADD COLUMN language TEXT')
        connection.execute('''
            CREATE TABLE IF NOT EXISTS sent_notices (
                birthday_id INTEGER,
                date TEXT,
                PRIMARY KEY (birthday_id, date)
            )
        ''')
        _migrate_legacy_values(connection)
        connection.commit()


# --- Birthdays ---
def add_birthday(chat_id, name, day_month, birth_year, category, phone):
    _execute('''
        INSERT INTO birthdays (chat_id, name, day_month, birth_year, category, phone)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (chat_id, name, day_month, birth_year, category, phone))


def get_birthdays_on(day_month):
    rows, _ = _execute(f'SELECT {_BIRTHDAY_COLUMNS} FROM birthdays WHERE day_month = ?', (day_month,), 'all')
    return rows


def get_all_birthdays():
    rows, _ = _execute(f'SELECT {_BIRTHDAY_COLUMNS} FROM birthdays', fetch='all')
    return rows


def get_birthday(birthday_id, chat_id=None):
    """If chat_id is given, only returns the birthday when it belongs to that user."""
    sql = f'SELECT {_BIRTHDAY_COLUMNS} FROM birthdays WHERE id = ?'
    params = [birthday_id]
    if chat_id is not None:
        sql += ' AND chat_id = ?'
        params.append(chat_id)
    row, _ = _execute(sql, params, 'one')
    return row


def get_birthdays_by_user(chat_id):
    rows, _ = _execute(
        'SELECT id, name, day_month, birth_year, category, phone FROM birthdays WHERE chat_id = ?', (chat_id,), 'all')
    return rows


def update_birthday(birthday_id, chat_id, **fields):
    """Update fields of a user's birthday. Returns True if something changed."""
    if not fields or any(field not in EDITABLE_FIELDS for field in fields):
        raise ValueError(f"Fields not editable: {list(fields)}")
    assignments = ", ".join(f"{field} = ?" for field in fields)
    _, rows = _execute(f'UPDATE birthdays SET {assignments} WHERE id = ? AND chat_id = ?',
                       (*fields.values(), birthday_id, chat_id))
    return rows > 0


def delete_birthday_by_name(chat_id, name):
    _, rows = _execute('DELETE FROM birthdays WHERE chat_id = ? AND name = ?', (chat_id, name))
    return rows > 0


def delete_birthday(birthday_id, chat_id=None):
    """Delete a birthday. If chat_id is given, only when it belongs to that user. Returns True if deleted."""
    sql, params = 'DELETE FROM birthdays WHERE id = ?', [birthday_id]
    if chat_id is not None:
        sql += ' AND chat_id = ?'
        params.append(chat_id)
    _, rows = _execute(sql, params)
    if rows:
        _execute('DELETE FROM sent_notices WHERE birthday_id = ?', (birthday_id,))
    return rows > 0


# --- Preferences ---
def get_settings(chat_id):
    """Returns {'hour', 'timezone', 'timezone_set', 'language', 'language_set'} with defaults if not chosen yet."""
    row, _ = _execute('SELECT alarm_hour, timezone, language FROM preferences WHERE chat_id = ?', (chat_id,), 'one')
    hour = (row[0] if row else None) or DEFAULT_HOUR
    timezone = row[1] if row else None
    language = row[2] if row else None
    return {'hour': hour, 'timezone': timezone or DEFAULT_TIMEZONE, 'timezone_set': bool(timezone),
            'language': language or DEFAULT_LANGUAGE, 'language_set': bool(language)}


def save_alarm_hour(chat_id, hour):
    _execute('''
        INSERT INTO preferences (chat_id, alarm_hour)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET alarm_hour=excluded.alarm_hour
    ''', (chat_id, hour))


def save_timezone(chat_id, timezone):
    _execute('''
        INSERT INTO preferences (chat_id, alarm_hour, timezone)
        VALUES (?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET timezone=excluded.timezone
    ''', (chat_id, DEFAULT_HOUR, timezone))


def save_language(chat_id, language):
    _execute('''
        INSERT INTO preferences (chat_id, alarm_hour, language)
        VALUES (?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET language=excluded.language
    ''', (chat_id, DEFAULT_HOUR, language))


# --- Sent notices (avoid duplicates if the cron fires twice) ---
def claim_notice(birthday_id, iso_date):
    """Mark the notice as sent. Returns False if it was already marked."""
    _, rows = _execute('INSERT OR IGNORE INTO sent_notices (birthday_id, date) VALUES (?, ?)',
                       (birthday_id, iso_date))
    return rows > 0


def release_notice(birthday_id, iso_date):
    _execute('DELETE FROM sent_notices WHERE birthday_id = ? AND date = ?', (birthday_id, iso_date))


if __name__ == '__main__':
    create_database()
    print("Database ready at:", DB_PATH)
