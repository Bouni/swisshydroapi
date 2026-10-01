"""Docker healthcheck: BAFU data must be fresh and the API must answer."""

import sys
import time
import urllib.request

from app.config import settings

MAX_AGE = 1 * 60 * 60

for feed in settings.feeds:
    file = settings.data_dir / f"{feed}.xml"
    try:
        age = time.time() - file.stat().st_mtime
    except OSError:
        sys.exit(f"File '{file}' does not exist, exit with error!")
    if age > MAX_AGE:
        sys.exit(f"File '{file}' older than 1h, exit with error!")

try:
    with urllib.request.urlopen("http://127.0.0.1/api/v1/stations", timeout=5) as r:
        if r.status != 200:
            sys.exit(f"API returned status {r.status}, exit with error!")
except Exception as e:
    sys.exit(f"API not reachable: {e}")
