import os
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="SwissHydroAPI", version=os.environ.get("APIVERSION", "2.0"),)

templates = Jinja2Templates(directory="templates")


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
async def root(request: Request):
    """ Auto redirect to docs"""
    return templates.TemplateResponse("index.j2", {"request": request})


@app.get("/stations", tags=["stations"])
async def stations():
    """
    Get a list of all stations
    """
    with open("station_list.json") as j:
        data = json.load(j)
    return data


@app.get("/station/{id_or_name}", tags=["stations"])
async def station(id_or_name):
    """
    Get all data for a given station by its ID or name
    """
    with open("station_data.json") as j:
        data = json.load(j)
    if id_or_name in data:
        return data[id_or_name]
    station = None
    for _, v in data.items():
        if v["name"] == id_or_name:
            station = v
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    return station
