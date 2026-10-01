import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(populated):
    # not used as context manager, so the lifespan (BAFU updater) does not run
    return TestClient(app)


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "SwissHydroApi" in r.text


def test_docs(client):
    assert client.get("/docs").status_code == 200


def test_stations(client):
    r = client.get("/api/v1/stations")
    assert r.status_code == 200
    assert [s["id"] for s in r.json()] == ["2009", "2016"]


def test_stations_data(client):
    r = client.get("/api/v1/stations/data")
    assert r.status_code == 200
    assert set(r.json()) == {"2009", "2016"}


@pytest.mark.parametrize("key", ["2009", "Porte du Scex"])
def test_station_by_id_or_name(client, key):
    r = client.get(f"/api/v1/station/{key}")
    assert r.status_code == 200
    assert r.json()["water-body-name"] == "Rhone"


def test_station_not_found(client):
    r = client.get("/api/v1/station/nope")
    assert r.status_code == 404
    assert r.json() == {"detail": "Station not found"}
