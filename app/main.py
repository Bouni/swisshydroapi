import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from . import bafu
from .config import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)-9s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Fetch BAFU data in a background task while the API is running"""
    updater = asyncio.create_task(bafu.run_forever(), name="bafu")
    yield
    updater.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await updater


app = FastAPI(title="SwissHydroAPI", version=settings.apiversion, lifespan=lifespan)

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def load(filename: str) -> Any:
    with open(settings.data_dir / filename) as j:
        return json.load(j)


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
async def root(request: Request):
    """Landing page"""
    return templates.TemplateResponse(request, "index.html")


# Endpoints are sync so file reads and JSON parsing run in the threadpool, not on the event loop


@app.get("/api/v1/stations", tags=["stations"])
def stations():
    """
    Get a list of all stations
    """
    return load("station_list.json")


@app.get("/api/v1/stations/data", tags=["stations"])
def stations_data():
    """
    Get a list of all stations with data
    """
    return load("station_data.json")


@app.get("/api/v1/station/{id_or_name}", tags=["stations"])
def station(id_or_name: str):
    """
    Get all data for a given station by its ID or name
    """
    data = load("station_data.json")
    # if id is passed
    if id_or_name in data:
        return data[id_or_name]
    # if name is passed
    for v in data.values():
        if v["name"] == id_or_name:
            return v
    # if no match is found
    raise HTTPException(status_code=404, detail="Station not found")
