import asyncio
import logging
import os
import threading

from dotenv import load_dotenv
from flask import Flask, Response, request
from telegram import Update
from telegram.ext import Application

import database as db
from alarms import send_alarms
from handlers import bot_commands, register_handlers
from telegram_request import RetryingRequest

load_dotenv()
TOKEN = os.getenv("TOKEN")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

# The bot lives in its own asyncio loop (background thread) and is started the first time it is needed.
ptb_app = None
loop = None
_startup_lock = threading.Lock()


def ensure_bot():
    """Start (once) the asyncio loop and the Telegram application. Returns (app, loop)."""
    global ptb_app, loop
    with _startup_lock:
        if ptb_app is None:
            if not TOKEN:
                raise RuntimeError("Missing environment variable TOKEN (define it in .env)")
            db.create_database()
            new_loop = asyncio.new_event_loop()
            threading.Thread(target=new_loop.run_forever, daemon=True).start()

            async def start_bot():
                # Built inside the bot loop (Python 3.9 needs a running loop to create the application)
                application = Application.builder().token(TOKEN).request(RetryingRequest()).build()
                register_handlers(application)
                await application.initialize()
                # Spanish menu for Spanish clients, English for everybody else
                await application.bot.set_my_commands(bot_commands('es'), language_code='es')
                await application.bot.set_my_commands(bot_commands('en'))
                return application

            application = asyncio.run_coroutine_threadsafe(start_bot(), new_loop).result()
            ptb_app, loop = application, new_loop
    return ptb_app, loop


def _run_in_background(coro, target_loop):
    future = asyncio.run_coroutine_threadsafe(coro, target_loop)
    future.add_done_callback(lambda f: f.exception() and logger.error("Error in background task", exc_info=f.exception()))


@flask_app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    """Route called by Telegram"""
    application, bot_loop = ensure_bot()
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return Response('Invalid request', status=400)
    update = Update.de_json(payload, application.bot)
    _run_in_background(application.process_update(update), bot_loop)
    return Response('OK', status=200)


@flask_app.route(f'/secret_alarm_{TOKEN}', methods=['GET'])
def trigger_alarms():
    """Secret route for the cron job. Must be called every hour on the hour."""
    application, bot_loop = ensure_bot()
    _run_in_background(send_alarms(application.bot), bot_loop)
    return Response('Alarms processed', status=200)


@flask_app.route(f'/force_alarm_{TOKEN}', methods=['GET'])
def force_alarms():
    """Developer route: send today's notices right now, ignoring the hour."""
    application, bot_loop = ensure_bot()
    _run_in_background(send_alarms(application.bot, force=True), bot_loop)
    return Response('Test alarm sent', status=200)


@flask_app.route('/', methods=['GET'])
def index():
    return "Cumpleping is running in webhook mode"


if __name__ == '__main__':
    flask_app.run(host='0.0.0.0', port=5000)
