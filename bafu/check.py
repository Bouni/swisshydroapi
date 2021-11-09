#!/usr/bin/python

import os
import sys
from datetime import datetime, timedelta

def file_to_old(file, delta): 
    cutoff = datetime.utcnow() - timedelta(seconds=delta)
    mtime = datetime.utcfromtimestamp(os.path.getmtime(file))
    if mtime < cutoff:
        return True
    return False

if file_to_old("/data/bafu_url_2.xml", 1*60*60):
    sys.exit(f"File '{bafu_2_file}' older than 1h, exit with error!")
if file_to_old("/data/bafu_url_6.xml", 1*60*60):
    sys.exit(f"File '{bafu_6_file}' older than 1h, exit with error!")
sys.exit(0)


