# 🎂 Cumpleping

A Telegram bot that remembers your people's birthdays and prepares the greeting for you (with their name and, if you know it, the age they turn), ready to copy or send through WhatsApp/Telegram.

**Stack:** Python · Flask webhook · python-telegram-bot · SQLite · hosted on [PythonAnywhere](https://www.pythonanywhere.com) · hourly trigger from [cron-job.org](https://cron-job.org).

## Commands

| Command | What it does |
|---|---|
| `/start` | Welcome and time zone selection the first time |
| `/new` (`/nuevo`) | Add a birthday: name → month → day → year (optional) → category → phone (optional) |
| `/list` (`/listar`) | Next 30 days, this month or all (paginated). Tap a name to **✏️ Edit** (name, date, year, category, phone) or **🗑️ Delete** (with confirmation) |
| `/settings` (`/ajustes`) | Reminder hour (any hour from 00:00 to 23:00), time zone and language |
| `/timezone [Continent/City]` (`/zona`) | Change the zone by typing it (e.g. `/timezone Europe/Paris`) or show the picker |
| `/export` (`/exportar`) | CSV backup |
| `/language` (`/idioma`) | Switch language (Spanish / English) |
| `/cancel` (`/cancelar`) | Cancel the creation or edit in progress |
| `/help` (`/ayuda`) | List of commands |

### Languages
The bot speaks **Spanish and English**. The language is detected the first time you write, from the `language_code` Telegram sends (`es`, `es-MX`… → Spanish; `en`, `en-GB`… → English; any other language → English; no data → Spanish). It is stored and can be changed in `/settings` or with `/language`. Automatic reminders are sent in the stored language. Every command has a Spanish and an English name, and Telegram's command menu is shown in the client's language.

To add another language: add its code to `SUPPORTED_LANGUAGES` and its texts to `i18n.py` (`STRINGS`, `COMMAND_DESCRIPTIONS`), `categories.py` (`LABELS`), `zones.py`, `messages.py` (`SUGGESTIONS`) and `age_facts.py` (one more column per fact). The tests check that all languages have the same keys and placeholders.

### Hours and time zones
Telegram does not tell bots the user's time zone, so each user picks it (Spain, Canary Islands, Mexico, Colombia, Argentina… or any zone with `/timezone`). The reminder arrives at the **chosen hour in their local time**: a user in Mexico with 09:00 is notified at 09:00 Mexico time, and one in Spain at 09:00 Spain time. If no zone has been chosen, `Europe/Madrid` is used.

### Greetings
Messages include the person's name and, when the birth year is known, the age they turn.

- **8 categories** to group contacts: Family, Friends, Partner, Work, School, Sports, Neighbors and None, each with its own tone and 5-7 messages.
- **Age fun facts** (when the birth year is known): "You are now older than the oldest dog on record", "At 2 you have lived as long as a round trip to Mars takes"… and, for almost every age, something that happened to a famous person at exactly that age (Mozart, Joan of Arc, Messi, Napoleon, Marilyn, Elvis, Picasso…). There are also **calculated facts** from the exact birth date: days, weeks, months, hours, minutes and seconds lived, Earth's laps around the Sun and kilometres travelled (~940 million per lap), Moon cycles, your age on Mars, Mercury and Jupiter. Historical facts are verifiable and statistics-free; when sources disagree, the text says so ("according to legend").
- **Each message is a single thing**, never a mix: a category greeting (50 %), a famous-person fact with a joke about it (25 %) or a calculated fact with a friendly closing (25 %). The last two only appear when the birth year is known.
- The "🔄 Another one" button never repeats the current message or fact.
- People born on 29 February are greeted on 28 February in non-leap years.

To add categories, edit `categories.py` and add their messages in `messages.py`; to add fun facts, edit `age_facts.py`.

## Getting started

Requires Python 3.9+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "TOKEN=<token from @BotFather>" > .env
python web.py                      # Flask server on port 5000
```
In production use a WSGI server (see the PythonAnywhere section below, or e.g. `gunicorn web:flask_app`). The SQLite database (`cumpleping.db`) is created and migrated automatically on startup; you can change its path with the `CUMPLEPING_DB` environment variable.

### Webhook and reminders
1. Register the webhook: `https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://YOUR_DOMAIN/<TOKEN>`
2. Schedule a cron job (we use **cron-job.org**) that calls `GET https://YOUR_DOMAIN/secret_alarm_<TOKEN>` **every hour on the hour**. Each call notifies the users for whom it is their chosen hour in their local time. Each birthday is notified only once a day even if the cron fires repeatedly.
3. For testing, `GET /force_alarm_<TOKEN>` sends today's reminders regardless of the hour.

## Deployment: PythonAnywhere + cron-job.org

Cumpleping runs on a [PythonAnywhere](https://www.pythonanywhere.com) web app (Flask/WSGI), and [cron-job.org](https://cron-job.org) acts as the scheduler that triggers the hourly reminders (a free PythonAnywhere account has no per-hour scheduled tasks, and the web app needs an external caller anyway).

1. **Upload the code.** Put all the `.py` files (including `telegram_request.py`) in your PythonAnywhere account, create a virtualenv and run `pip install -r requirements.txt`.
2. **Create the web app** (manual configuration, Flask) and point the WSGI file to `flask_app`:
   ```python
   import sys
   sys.path.insert(0, '/home/<user>/cumpleping')
   from web import flask_app as application
   ```
   Put `TOKEN=...` in a `.env` file next to `web.py`, then **Reload** the web app. The database is migrated automatically.
3. **Set the Telegram webhook** to `https://<user>.pythonanywhere.com/<TOKEN>` (see above).
4. **Create the cron job on cron-job.org**: URL `https://<user>.pythonanywhere.com/secret_alarm_<TOKEN>`, schedule *every hour at minute 0*. Keep that URL private: it contains the bot token.
5. Free PythonAnywhere accounts reach the internet through a proxy that sometimes returns `503`. `telegram_request.py` retries up to 3 times on proxy/connection failures (only those that happen before Telegram receives the request, so messages are never duplicated) and enlarges the connection pool; network errors that still fail are logged as a warning without a traceback.

## Structure

| File | Contents |
|---|---|
| `web.py` | Flask: webhook and alarm routes; starts the bot in a background asyncio loop |
| `handlers.py` | Commands, buttons and conversations (create and edit) |
| `alarms.py` | Per-user / per-time-zone reminder sending logic |
| `database.py` | SQLite (`birthdays`, `preferences`, `sent_notices`) and migration of old databases |
| `dates.py` | Days left, ages, 29 February |
| `categories.py` | Contact categories |
| `messages.py`, `age_facts.py` | Greeting templates and age fun facts (es/en) |
| `i18n.py` | Texts in each language and language detection |
| `zones.py`, `validation.py` | Time zones and phone prefixes; name/phone validation |
| `telegram_request.py` | HTTP request class with retries for PythonAnywhere's proxy |

The code is in English; the user-facing texts live in `i18n.py` (Spanish and English).

### Databases from earlier versions
On startup, `database.create_database()` automatically migrates databases with the old Spanish schema (tables `cumpleaños`/`preferencias`, categories "Familia"…, year "Desconocido"). Back up `cumpleping.db` before the first start if you want to be safe.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```
Tests use a temporary database and mocked Telegram objects: they need no network or real token.
