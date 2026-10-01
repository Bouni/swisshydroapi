from pathlib import Path

import pytest

from app import bafu
from app.config import settings

FEED = Path(__file__).parent / "feed.xml"


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    return tmp_path


@pytest.fixture
def populated(data_dir):
    data = {}
    bafu.parse(FEED.read_bytes(), data)
    bafu.write_output({"bafu_url_2": FEED.read_text(), "bafu_url_6": FEED.read_text()}, data)
    return data_dir
