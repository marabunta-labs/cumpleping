import asyncio
import threading
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

import web


@pytest.fixture
def client(monkeypatch):
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    fake_app = MagicMock()
    fake_app.process_update = AsyncMock()
    monkeypatch.setattr(web, "ensure_bot", lambda: (fake_app, loop))
    monkeypatch.setattr(web.Update, "de_json", staticmethod(lambda payload, bot: ("update", payload)))
    yield web.flask_app.test_client(), fake_app
    loop.call_soon_threadsafe(loop.stop)


def wait_for(condition, seconds=2):
    end = time.time() + seconds
    while time.time() < end:
        if condition():
            return True
        time.sleep(0.01)
    return False


def test_index(client):
    response = client[0].get("/")
    assert response.status_code == 200 and "Cumpleping" in response.get_data(as_text=True)


def test_webhook_processes_update(client):
    c, app = client
    assert c.post(f"/{web.TOKEN}", json={"update_id": 1}).status_code == 200
    assert wait_for(lambda: app.process_update.await_count == 1)


def test_webhook_rejects_empty_or_invalid_requests(client):
    c, app = client
    assert c.post(f"/{web.TOKEN}", data="not json").status_code == 400
    assert c.post(f"/{web.TOKEN}", json={}).status_code == 400
    app.process_update.assert_not_awaited()


def test_webhook_with_wrong_token_is_404(client):
    assert client[0].post("/other-token", json={"update_id": 1}).status_code == 404


def test_webhook_does_not_accept_get(client):
    assert client[0].get(f"/{web.TOKEN}").status_code == 405


def test_alarm_routes(client, monkeypatch):
    calls = []

    async def fake(bot, force=False):
        calls.append(force)
    monkeypatch.setattr(web, "send_alarms", fake)
    c, _ = client
    assert c.get(f"/secret_alarm_{web.TOKEN}").status_code == 200
    assert wait_for(lambda: calls == [False])
    assert c.get(f"/force_alarm_{web.TOKEN}").status_code == 200
    assert wait_for(lambda: calls == [False, True])
    assert c.get("/secret_alarm_wrong").status_code == 404


def test_ensure_bot_requires_token(monkeypatch):
    monkeypatch.setattr(web, "ptb_app", None)
    monkeypatch.setattr(web, "TOKEN", None)
    with pytest.raises(RuntimeError, match="TOKEN"):
        web.ensure_bot()
