import json
import sys
import os
import signal
import time

import requests
import xmltodict


class XML2JSON:
    def __init__(self):
        self.data = {}
        self.fetch("bafu_url_2")
        self.parse(self.data)
        self.fetch("bafu_url_6")
        self.parse(self.data)
        self.write()
        self.killed = False

    def _handler(self, signum, frame):
        print("Received SIGINT or SIGTERM! Finishing this block, then exiting.")
        self.killed = True

    def __enter__(self):
        self.old_sigint = signal.signal(signal.SIGINT, self._handler)
        self.old_sigterm = signal.signal(signal.SIGTERM, self._handler)

    def __exit__(self, type, value, traceback):
        if self.killed:
            sys.exit(0)
        signal.signal(signal.SIGINT, self.old_sigint)
        signal.signal(signal.SIGTERM, self.old_sigterm)

    def CH1903toWGS1984(self, east, north):
        """
        function to convert SwisGrid coordinates to WSG84 aka Google Coordinates :-)
        http://www.giangrandi.ch/soft/swissgrid/swissgrid.shtml
        """
        east = self.to_float(east)
        north = self.to_float(north)
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

    @staticmethod
    def to_float(v):
        """try to convert str to float, return empty string if not possible."""
        try:
            v = float(v)
        except:
            v = v
        return v

    def parse_values(self, parameter):
        """ Parse parameter values from xml """
        values = {
            "unit": parameter["@unit"],
            "datetime": parameter["datetime"],
        }
        for p in parameter:
            if p.startswith("@"):
                continue
            if isinstance(parameter[p], str):
                values[p] = self.to_float(parameter[p])
            else:
                values[p] = self.to_float(parameter[p]["#text"])
        return values

    def parse(self, target):
        """Parse data for every station."""
        xml = xmltodict.parse(self.xml, force_list=("parameter",))
        for station in xml["locations"]["station"]:
            target[station["@number"]] = {
                "name": station["@name"],
                "water-body-name": station["@water-body-name"],
                "water-body-type": station["@water-body-type"],
                "coordinates": self.CH1903toWGS1984(
                    station["@easting"], station["@northing"]
                ),
                "parameters": {},
            }
            translations = {"wassertemperatur": "temperature", "abfluss": "discharge", "pegel": "level"}
            # if no parameters are available for this station continue with the next
            if not "parameter" in station:
                print(f"Station {station['@name']} does not provide any parameters, continue with next")
                continue
            for parameter in station["parameter"]:
                name = translations.get(parameter["@name"].split(" ")[0].lower(), None)
                if not name:
                    print(f"Failed to get name for parameter {parameter['@name']} of station {station['@name']}")
                    continue
                target[station["@number"]]["parameters"][name] = self.parse_values(
                    parameter
                )

    def fetch(self, url):
        r = requests.get(
            os.environ.get(url, None),
            auth=(os.environ.get("bafu_user", None), os.environ.get("bafu_pass", None)),
        )
        if r.ok:
            print(f"Sucessfully fetched {os.environ.get(url)}")
        else:
            print(f"Error {r.status_code}, {r.text}")
        with open(f"/data/{url}.xml", "w") as x:
            x.write(r.text)
        self.xml = r.content

    def write(self):
        with open("/data/station_list.json", "w") as j:
            stations = [
                {
                    "id": k,
                    "name": v["name"],
                    "water-body-name": v["water-body-name"],
                    "water-body-type": v["water-body-type"],
                }
                for k, v in self.data.items()
            ]
            json.dump(
                stations,
                j,
            )
        with open("/data/station_data.json", "w") as j:
            json.dump(
                self.data,
                j,
            )


if __name__ == "__main__":
    try:
        while True:
            # get data from bafu, convert it and save it
            XML2JSON()
            # sleep for 10 minutes
            time.sleep(10 * 60)
    except KeyboardInterrupt as ex:
        print("received keyboard interrupt, exit")
