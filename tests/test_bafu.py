import asyncio
import json
import time

import httpx2
import pytest

from app import bafu
from app.config import settings

from .conftest import FEED

RealAsyncClient = httpx2.AsyncClient


def test_parse():
    data = {}
    bafu.parse(FEED.read_bytes(), data)
    assert set(data) == {"2009", "2016"}
    scex = data["2009"]
    assert scex["name"] == "Porte du Scex"
    assert scex["coordinates"] == pytest.approx({"latitude": 46.3497, "longitude": 6.8889}, abs=1e-3)
    assert scex["parameters"]["discharge"] == {
        "unit": "m3/s",
        "datetime": "2026-10-01T12:00:00+01:00",
        "value": 123.4,
        "max-24h": 140.0,
    }
    assert scex["parameters"]["temperature"]["value"] == 11.2
    assert data["2016"]["parameters"] == {}


def test_write_output(populated):
    assert json.loads((populated / "station_list.json").read_text())[0] == {
        "id": "2009",
        "name": "Porte du Scex",
        "water-body-name": "Rhone",
        "water-body-type": "river",
    }
    assert "2016" in json.loads((populated / "station_data.json").read_text())
    assert (populated / "bafu_url_2.xml").exists()


def test_rate_limit_persisted(data_dir):
    assert bafu.seconds_until_next_fetch() <= 0
    (data_dir / ".last_fetch").write_text(str(time.time() - 120))
    assert bafu.seconds_until_next_fetch() == pytest.approx(480, abs=2)


def mock_transport(status=200):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx2.Response(status, content=FEED.read_bytes())

    return httpx2.MockTransport(handler), calls


def run_once(monkeypatch, transport):
    """Run the updater loop until it goes to sleep."""
    monkeypatch.setattr(settings, "bafu_url_2", "https://bafu.test/2")
    monkeypatch.setattr(settings, "bafu_url_6", "https://bafu.test/6")
    monkeypatch.setattr(bafu.httpx2, "AsyncClient", lambda **kw: RealAsyncClient(transport=transport, **kw))

    async def stop(_):
        raise asyncio.CancelledError

    monkeypatch.setattr(bafu.asyncio, "sleep", stop)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(bafu.run_forever())


def test_run_forever_fetches_once(data_dir, monkeypatch):
    transport, calls = mock_transport()
    run_once(monkeypatch, transport)
    assert sorted(calls) == ["https://bafu.test/2", "https://bafu.test/6"]
    assert (data_dir / "station_data.json").exists()
    # a restart right after must not fetch again
    run_once(monkeypatch, transport)
    assert len(calls) == 2


def test_failed_fetch_keeps_old_data(populated, monkeypatch):
    before = (populated / "station_data.json").read_text()
    transport, calls = mock_transport(status=500)
    run_once(monkeypatch, transport)
    assert calls
    assert (populated / "station_data.json").read_text() == before
    assert bafu.seconds_until_next_fetch() > 0
