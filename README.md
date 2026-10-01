# swisshydroapi

A RESTful API for the data of [FOEN](https://www.hydrodaten.admin.ch/en/) for the usage in [Home-Assistant](http://home-assistant.io/).

Currently hosted at https://swisshydroapi.bouni.de
                        
# Support this project

<a href="https://ko-fi.com/I3I364QTM" target="_blank"><img src="https://ko-fi.com/img/githubbutton_sm.svg" style="height: 30px !important"/></a>
<a href="https://www.buymeacoffee.com/bouni" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" style="height: 30px !important"/></a>
<a href="https://github.com/sponsors/Bouni" target="_blank"><img src="https://img.shields.io/badge/-Github Sponsor-fafbfc?style=flat&logo=GitHub%20Sponsors" style="height: 30px !important"/></a>

# Running

API and BAFU fetcher run in a single container. The fetcher runs as a background task of the API and
polls BAFU at most once every 10 minutes (the last attempt is stored in `/data/.last_fetch`, so this also
holds across restarts).

```sh
docker build -t swisshydroapi .
docker run -d -p 80:80 -v hydrodata:/data \
  -e bafu_url_2=... -e bafu_url_6=... \
  -e bafu_user=... -e bafu_pass=... \
  -e bafu_healthcheck=... \
  swisshydroapi
```

# Development

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync                                        # create .venv with all dependencies
DATA_DIR=./data uv run uvicorn app.main:app --reload
uv run pytest
uv run ruff check . && uv run ruff format .
```
