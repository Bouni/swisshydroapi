import asyncio
import fcntl
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx2
import xmltodict

from .config import settings

log = logging.getLogger(__name__)

# FOEN allows polling at most every 10 minutes
FETCH_INTERVAL = 10 * 60
REQUEST_TIMEOUT = 60
HEALTHCHECK_URL = "https://healthchecks.bouni.de/ping"

TRANSLATIONS = {"wassertemperatur": "temperature", "abfluss": "discharge", "pegel": "level"}


def CH1903toWGS1984(east: str | float, north: str | float) -> dict[str, float]:
    """
    function to convert SwisGrid coordinates to WSG84 aka Google Coordinates :-)
    http://www.giangrandi.ch/soft/swissgrid/swissgrid.shtml
    """
    east = float(east)
    north = float(north)
    # Convert origin to "civil" system, where Bern has coordinates 0,0.
    east -= 600000
    north -= 200000
    # Express distances in 1000km units.
    east /= 1e6
    north /= 1e6
    # Calculate longitude in 10000" units.
    lon = 2.6779094
    lon += 4.728982 * east
    lon += 0.791484 * east * north
    lon += 0.1306 * east * north * north
    lon -= 0.0436 * east * east * east
    # Calculate latitude in 10000" units.
    lat = 16.9023892
    lat += 3.238272 * north
    lat -= 0.270978 * east * east
    lat -= 0.002528 * north * north
    lat -= 0.0447 * east * east * north
    lat -= 0.0140 * north * north * north
    # Convert longitude and latitude back in degrees.
    lon *= 100 / 36
    lat *= 100 / 36
    return {"latitude": lat, "longitude": lon}


def to_float(v: Any) -> Any:
    """try to convert str to float, return the value unchanged if not possible."""
    try:
        return float(v)
    except TypeError, ValueError:
        return v


def parse_values(parameter: dict[str, Any]) -> dict[str, Any]:
    """Parse parameter values from xml"""
    values = {
        "unit": parameter["@unit"],
        "datetime": parameter["datetime"],
    }
    for p, v in parameter.items():
        if p.startswith("@"):
            continue
        values[p] = to_float(v if isinstance(v, str) else v["#text"])
    return values


def parse(xml: bytes, target: dict[str, Any]) -> None:
    """Parse data for every station."""
    doc = xmltodict.parse(xml, force_list=("parameter", "station"))
    for station in doc["locations"]["station"]:
        target[station["@number"]] = {
            "name": station["@name"],
            "water-body-name": station["@water-body-name"],
            "water-body-type": station["@water-body-type"],
            "coordinates": CH1903toWGS1984(station["@easting"], station["@northing"]),
            "parameters": {},
        }
        # if no parameters are available for this station continue with the next
        if "parameter" not in station:
            log.debug("Station %s does not provide any parameters", station["@name"])
            continue
        for parameter in station["parameter"]:
            name = TRANSLATIONS.get(parameter["@name"].split(" ")[0].lower())
            if not name:
                log.info("Failed to get name for parameter %s of station %s", parameter["@name"], station["@name"])
                continue
            target[station["@number"]]["parameters"][name] = parse_values(parameter)


def station_list(data: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "id": k,
            "name": v["name"],
            "water-body-name": v["water-body-name"],
            "water-body-type": v["water-body-type"],
        }
        for k, v in data.items()
    ]


def write_atomic(path: Path, data: str) -> None:
    """Write to a temp file and rename it so readers never see a partial file."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(data)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def write_output(xmls: dict[str, str], data: dict[str, Any]) -> None:
    data_dir = settings.data_dir
    for feed, xml in xmls.items():
        write_atomic(data_dir / f"{feed}.xml", xml)
    write_atomic(data_dir / "station_list.json", json.dumps(station_list(data)))
    write_atomic(data_dir / "station_data.json", json.dumps(data))


async def fetch(client: httpx2.AsyncClient, feed: str, url: str | None) -> httpx2.Response:
    if not url:
        raise RuntimeError(f"Environment variable {feed} is not set")
    r = await client.get(url)
    r.raise_for_status()
    log.info("Successfully fetched %s", url)
    return r


async def update(client: httpx2.AsyncClient) -> None:
    """Fetch all feeds and only write output if everything succeeded."""
    responses = await asyncio.gather(*(fetch(client, feed, url) for feed, url in settings.feeds.items()))
    data: dict[str, Any] = {}
    for r in responses:
        await asyncio.to_thread(parse, r.content, data)
    xmls = {feed: r.text for feed, r in zip(settings.feeds, responses, strict=True)}
    await asyncio.to_thread(write_output, xmls, data)
    log.info("Updated data for %d stations", len(data))


async def ping_healthcheck(client: httpx2.AsyncClient, success: bool) -> None:
    if not settings.bafu_healthcheck:
        return
    url = f"{HEALTHCHECK_URL}/{settings.bafu_healthcheck}" + ("" if success else "/fail")
    try:
        await client.get(url, timeout=10)
        log.info("Sent %s ping to healthchecks.bouni.de", "SUCCESS" if success else "FAIL")
    except httpx2.HTTPError as e:
        log.warning("Healthcheck ping failed: %s", e)


def last_fetch() -> float:
    try:
        return float((settings.data_dir / ".last_fetch").read_text().strip())
    except OSError, ValueError:
        return 0.0


def seconds_until_next_fetch() -> float:
    return last_fetch() + FETCH_INTERVAL - time.time()


async def run_forever() -> None:
    """Run update() at most once every FETCH_INTERVAL seconds until cancelled.

    The time of the last attempt is persisted in the data dir so the interval also holds across restarts.
    A file lock makes sure only one process fetches, even when running multiple workers.
    """
    with open(settings.data_dir / ".bafu.lock", "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log.info("Another process is already fetching BAFU data, not starting updater")
            return

        auth = (settings.bafu_user, settings.bafu_pass) if settings.bafu_user else None
        async with httpx2.AsyncClient(auth=auth, timeout=REQUEST_TIMEOUT) as client:
            while True:
                wait = seconds_until_next_fetch()
                if wait > 0:
                    log.info("Next BAFU fetch in %.0fs", wait)
                    await asyncio.sleep(wait)
                    continue
                # record the attempt before fetching so failures count towards the rate limit too
                try:
                    write_atomic(settings.data_dir / ".last_fetch", str(time.time()))
                except OSError:
                    log.exception("Cannot record fetch time, retrying later")
                    await asyncio.sleep(FETCH_INTERVAL)
                    continue
                try:
                    await update(client)
                    await ping_healthcheck(client, True)
                except Exception:
                    log.exception("Updating BAFU data failed")
                    await ping_healthcheck(client, False)
