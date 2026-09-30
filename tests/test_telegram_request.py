import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram.error import NetworkError, TimedOut

import handlers as h
import telegram_request as tr
from conftest import make_context, make_update, run


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(tr, "BACKOFF_SECONDS", 0)


def make_request(monkeypatch, side_effects):
    request = tr.RetryingRequest()
    base = AsyncMock(side_effect=side_effects)
    monkeypatch.setattr(tr.HTTPXRequest, "do_request", base)
    return request, base


def test_retries_proxy_errors_until_it_works(monkeypatch):
    request, base = make_request(monkeypatch, [NetworkError("httpx.ProxyError: 503 Service Unavailable")] * 2 + [(200, b"ok")])
    assert run(request.do_request("url", "POST")) == (200, b"ok")
    assert base.await_count == 3


def test_gives_up_after_the_retries(monkeypatch):
    request, base = make_request(monkeypatch, [NetworkError("httpx.ProxyError: 503")] * 10)
    with pytest.raises(NetworkError):
        run(request.do_request("url", "POST"))
    assert base.await_count == tr.RETRIES + 1


@pytest.mark.parametrize("error", [TimedOut(), NetworkError("httpx.ReadError: connection reset")])
def test_does_not_retry_errors_that_may_have_reached_telegram(monkeypatch, error):
    request, base = make_request(monkeypatch, [error, (200, b"ok")])
    with pytest.raises(NetworkError):
        run(request.do_request("url", "POST"))
    assert base.await_count == 1


def test_pool_is_bigger_than_ptb_default():
    request = tr.RetryingRequest()
    assert tr.POOL_SIZE > 1
    assert request._client is not None


def test_error_handler_ignores_network_errors_without_replying():
    update = make_update(text="/settings")
    ctx = make_context()
    ctx.error = NetworkError("httpx.ProxyError: 503")
    run(h.error_handler(update, ctx))
    update.message.reply_text.assert_not_awaited()


def test_error_handler_still_replies_for_other_errors():
    update = make_update(text="/settings")
    update.__class__ = h.Update  # the handler only replies to real Telegram updates
    ctx = make_context()
    ctx.error = ValueError("boom")
    run(h.error_handler(update, ctx))
    update.message.reply_text.assert_awaited_once()
