import json
import math
import os

import requests
import xmltodict


class XML2JSON:
    def __init__(self):
        self.data = {}
        self.load_config()
        self.fetch()
        self.parse()
        self.write()

    def load_config(self):
        with open("config") as c:
            self.config = json.load(c)

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
            v = ""
        return v

    def parse_values(self, parameter):
        """ Parse parameter values from xml """
        if isinstance(parameter["value"], str):
            value = parameter["value"]
        else:
            value = parameter["value"]["#text"]
        if isinstance(parameter["max-24h"], str):
            max24h = parameter["max-24h"]
        else:
            max24h = parameter["max-24h"]["#text"]
        values = {
            "unit": parameter["@unit"],
            "datetime": parameter["datetime"],
            "value": self.to_float(value),
            "previous-24h": self.to_float(parameter["previous-24h"]),
            "delta-24h": self.to_float(parameter["delta-24h"]),
            "max-24h": self.to_float(max24h),
            "mean-24h": self.to_float(parameter["mean-24h"]),
            "min-24h": self.to_float(parameter["min-24h"]),
            "max-1h": self.to_float(parameter["max-1h"]),
            "mean-1h": self.to_float(parameter["mean-1h"]),
            "min-1h": self.to_float(parameter["min-1h"]),
        }
        return values

    def parse(self):
        """Parse data for every station."""
        self.data = {}
        xml = xmltodict.parse(self.xml)
        for station in xml["locations"]["station"]:
            self.data[station["@number"]] = {
                "name": station["@name"],
                "water-body-name": station["@water-body-name"],
                "water-body-type": station["@water-body-type"],
                "coordinates": self.CH1903toWGS1984(
                    station["@easting"], station["@northing"]
                ),
                "parameters": {},
            }
            translations = {"temperatur": "temperature", "abfluss": "discharge"}
            if isinstance(station["parameter"], list):
                for parameter in station["parameter"]:
                    name = translations.get(
                        parameter["@name"].split(" ")[0].lower(), "level"
                    )
                    self.data[station["@number"]]["parameters"][
                        name
                    ] = self.parse_values(parameter)
            else:
                parameter = station["parameter"]
                name = translations.get(
                    parameter["@name"].split(" ")[0].lower(), "level"
                )
                self.data[station["@number"]]["parameters"][name] = self.parse_values(
                    parameter
                )

    def fetch(self):
        r = requests.get(
            self.config["url"], auth=(self.config["user"], self.config["pass"])
        )
        self.xml = r.content

    def write(self):
        with open("station_list.json", "w") as j:
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
                stations, j,
            )
        with open("station_data.json", "w") as j:
            json.dump(
                self.data, j,
            )


if __name__ == "__main__":
    XML2JSON()
