import math
import xmltodict
from flask import Flask, request, send_from_directory
from flask_restful import Api, Resource, reqparse, abort
from flask_cache import Cache 

app = Flask(__name__, static_url_path='')
api = Api(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})


@app.route("/")
def docs():
    return send_from_directory('docs', 'docs.html')

def _float(v):
    if v == "NaN":
        return ""
    else:
        return float(v)

def CH1903toWGS1984(east, north):
    """ 
    function to convert SwisGrid coordinates to WSG84 aka Google Coordinates :-) 
    http://www.giangrandi.ch/soft/swissgrid/swissgrid.shtml 
    """
    east = _float(east)
    north = _float(north)
    east -= 600000                         # Convert origin to "civil" system, where Bern has coordinates 0,0.
    north -= 200000
    east /= 1E6                            # Express distances in 1000km units.
    north /= 1E6
    lon = 2.6779094                        # Calculate longitude in 10000" units.
    lon += 4.728982 * east
    lon += 0.791484 * east * north
    lon += 0.1306 * east * north * north
    lon -= 0.0436 * east * east * east
    lat = 16.9023892                       # Calculate latitude in 10000" units.
    lat += 3.238272 * north
    lat -= 0.270978 * east * east
    lat -= 0.002528 * north * north
    lat -= 0.0447 * east * east * north
    lat -= 0.0140 * north * north * north
    lon *= 100 / 36                        # Convert longitude and latitude back in degrees.
    lat *= 100 / 36
    return {"latitude": lat, "longitude": lon}


def parse_values(parameter):
    """ Parse parameter values from xm """
    if isinstance(parameter["value"], str):
        value = parameter["value"]
    else:
        value = parameter["value"]["#text"]
    if isinstance(parameter["max-24h"], str):
        max24h = parameter["max-24h"]
    else:
        max24h = parameter["max-24h"]["#text"]
    data = {
            "unit": parameter["@unit"],
            "datetime": parameter["datetime"],
            "value": _float(value),
            "previous-24h": _float(parameter["previous-24h"]),
            "delta-24h": _float(parameter["delta-24h"]),
            "max-24h": _float(max24h),
            "mean-24h": _float(parameter["mean-24h"]),
            "min-24h": _float(parameter["min-24h"]),
            "max-1h": _float(parameter["max-1h"]),
            "mean-1h": _float(parameter["mean-1h"]),
            "min-1h": _float(parameter["min-1h"])
        }
    return data


def refresh_data():
    """ refresh data from xml file int python object """
    data = {}
    with open('/srv/swisshydroapi/hydroweb.xml') as f:
        xml = xmltodict.parse(f.read())
        for station in xml["locations"]["station"]:
            data[station["@number"]] = {
                "name": station["@name"],
                "water-body-name": station["@water-body-name"],
                "water-body-type": station["@water-body-type"],
                "coordinates": CH1903toWGS1984(station["@easting"], station["@northing"]),
                "parameters": {}
            }
            if isinstance(station["parameter"], list):
                for parameter in station["parameter"]:
                    name = parameter["@name"].split(" ")[0].lower()
                    if name == "temperatur":
                        name = "temperature"
                    elif name == "abfluss":
                        name = "discharge"
                    else:
                        name = "level"
                    data[station["@number"]]["parameters"][name] = parse_values(parameter)
            else:
                parameter = station["parameter"]
                name = parameter["@name"].split(" ")[0].lower()
                if name == "temperatur":
                    name = "temperature"
                elif name == "abfluss":
                    name = "discharge"
                else:
                    name = "level"
                data[station["@number"]]["parameters"][name] = parse_values(parameter)
        return data

@cache.cached(timeout=60*10,key_prefix='data')
def get_data():
    return refresh_data()

class Clear(Resource):

    def get(self):
        return cache.clear() 

class Stations(Resource):

    def get(self):
        data = get_data()
        return [int(key) for key in data.keys()]

class Station(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        return data[stationid]

class StationName(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        return data[stationid]["name"]

class StationWaterBody(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        return data[stationid]["water-body-name"]

class StationWaterBodyType(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        return data[stationid]["water-body-type"]

class StationCoordinates(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        return data[stationid]["coordinates"]

class StationParameters(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        return data[stationid]["parameters"]

class StationParametersTemperature(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "temperature" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide temperature measurements")
        return data[stationid]["parameters"]["temperature"]

class StationParametersTemperatureUnit(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "temperature" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide temperature measurements")
        return data[stationid]["parameters"]["temperature"]["unit"]

class StationParametersTemperatureDatetime(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "temperature" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide temperature measurements")
        return data[stationid]["parameters"]["temperature"]["datetime"]

class StationParametersTemperatureValue(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "temperature" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide temperature measurements")
        return data[stationid]["parameters"]["temperature"]["value"]

class StationParametersTemperaturePrevious24h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "temperature" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide temperature measurements")
        return data[stationid]["parameters"]["temperature"]["previous-24h"]

class StationParametersTemperatureDelta24h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "temperature" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide temperature measurements")
        return data[stationid]["parameters"]["temperature"]["delta-24h"]

class StationParametersTemperatureMax24h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "temperature" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide temperature measurements")
        return data[stationid]["parameters"]["temperature"]["max-24h"]

class StationParametersTemperatureMean24h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "temperature" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide temperature measurements")
        return data[stationid]["parameters"]["temperature"]["mean-24h"]

class StationParametersTemperatureMin24h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "temperature" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide temperature measurements")
        return data[stationid]["parameters"]["temperature"]["min-24h"]

class StationParametersTemperatureMax1h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "temperature" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide temperature measurements")
        return data[stationid]["parameters"]["temperature"]["max-1h"]

class StationParametersTemperatureMean1h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "temperature" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide temperature measurements")
        return data[stationid]["parameters"]["temperature"]["mean-1h"]

class StationParametersTemperatureMin1h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "temperature" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide temperature measurements")
        return data[stationid]["parameters"]["temperature"]["min-1h"]

class StationParametersLevel(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "level" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide level measurements")
        return data[stationid]["parameters"]["level"]

class StationParametersLevelUnit(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "level" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide level measurements")
        return data[stationid]["parameters"]["level"]["unit"]

class StationParametersLevelDatetime(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "level" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide level measurements")
        return data[stationid]["parameters"]["level"]["datetime"]

class StationParametersLevelValue(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "level" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide level measurements")
        return data[stationid]["parameters"]["level"]["value"]

class StationParametersLevelPrevious24h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "level" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide level measurements")
        return data[stationid]["parameters"]["level"]["previous-24h"]

class StationParametersLevelDelta24h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "level" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide level measurements")
        return data[stationid]["parameters"]["level"]["delta-24h"]

class StationParametersLevelMax24h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "level" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide level measurements")
        return data[stationid]["parameters"]["level"]["max-24h"]

class StationParametersLevelMean24h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "level" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide level measurements")
        return data[stationid]["parameters"]["level"]["mean-24h"]

class StationParametersLevelMin24h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "level" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide level measurements")
        return data[stationid]["parameters"]["level"]["min-24h"]

class StationParametersLevelMax1h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "level" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide level measurements")
        return data[stationid]["parameters"]["level"]["max-1h"]

class StationParametersLevelMean1h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "level" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide level measurements")
        return data[stationid]["parameters"]["level"]["mean-1h"]

class StationParametersLevelMin1h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "level" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide level measurements")
        return data[stationid]["parameters"]["level"]["min-1h"]

class StationParametersDischarge(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "discharge" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide discharge measurements")
        return data[stationid]["parameters"]["discharge"]

class StationParametersDischargeUnit(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "discharge" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide discharge measurements")
        return data[stationid]["parameters"]["discharge"]["unit"]

class StationParametersDischargeDatetime(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "discharge" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide discharge measurements")
        return data[stationid]["parameters"]["discharge"]["datetime"]

class StationParametersDischargeValue(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "discharge" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide discharge measurements")
        return data[stationid]["parameters"]["discharge"]["value"]

class StationParametersDischargePrevious24h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "discharge" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide discharge measurements")
        return data[stationid]["parameters"]["discharge"]["previous-24h"]

class StationParametersDischargeDelta24h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "discharge" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide discharge measurements")
        return data[stationid]["parameters"]["discharge"]["delta-24h"]

class StationParametersDischargeMax24h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "discharge" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide discharge measurements")
        return data[stationid]["parameters"]["discharge"]["max-24h"]

class StationParametersDischargeMean24h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "discharge" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide discharge measurements")
        return data[stationid]["parameters"]["discharge"]["mean-24h"]

class StationParametersDischargeMin24h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "discharge" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide discharge measurements")
        return data[stationid]["parameters"]["discharge"]["min-24h"]

class StationParametersDischargeMax1h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "discharge" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide discharge measurements")
        return data[stationid]["parameters"]["discharge"]["max-1h"]

class StationParametersDischargeMean1h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "discharge" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide discharge measurements")
        return data[stationid]["parameters"]["discharge"]["mean-1h"]

class StationParametersDischargeMin1h(Resource):

    def get(self, stationid):
        data = get_data()
        if stationid not in data:
            abort(404, message="Invalid station id")
        if "discharge" not in data[stationid]["parameters"]:
            abort(404, message="Station does not provide discharge measurements")
        return data[stationid]["parameters"]["discharge"]["min-1h"]

api.add_resource(Clear, "/api/v1/cache/clear")
api.add_resource(Stations, "/api/v1/stations")
api.add_resource(Station, "/api/v1/station/<string:stationid>")
api.add_resource(StationName, "/api/v1/station/<string:stationid>/name")
api.add_resource(StationWaterBody, "/api/v1/station/<string:stationid>/water-body-name")
api.add_resource(StationWaterBodyType, "/api/v1/station/<string:stationid>/water-body-type")
api.add_resource(StationCoordinates, "/api/v1/station/<string:stationid>/coordinates")
api.add_resource(StationParameters, "/api/v1/station/<string:stationid>/parameters")
api.add_resource(StationParametersTemperature, "/api/v1/station/<string:stationid>/parameters/temperature")
api.add_resource(StationParametersTemperatureUnit, "/api/v1/station/<string:stationid>/parameters/temperature/unit")
api.add_resource(StationParametersTemperatureDatetime, "/api/v1/station/<string:stationid>/parameters/temperature/datetime")
api.add_resource(StationParametersTemperatureValue, "/api/v1/station/<string:stationid>/parameters/temperature/value")
api.add_resource(StationParametersTemperaturePrevious24h, "/api/v1/station/<string:stationid>/parameters/temperature/previous24h")
api.add_resource(StationParametersTemperatureDelta24h, "/api/v1/station/<string:stationid>/parameters/temperature/delta24h")
api.add_resource(StationParametersTemperatureMax24h, "/api/v1/station/<string:stationid>/parameters/temperature/max24h")
api.add_resource(StationParametersTemperatureMean24h, "/api/v1/station/<string:stationid>/parameters/temperature/mean24h")
api.add_resource(StationParametersTemperatureMin24h, "/api/v1/station/<string:stationid>/parameters/temperature/min24h")
api.add_resource(StationParametersTemperatureMax1h, "/api/v1/station/<string:stationid>/parameters/temperature/max1h")
api.add_resource(StationParametersTemperatureMean1h, "/api/v1/station/<string:stationid>/parameters/temperature/mean1h")
api.add_resource(StationParametersTemperatureMin1h, "/api/v1/station/<string:stationid>/parameters/temperature/min1h")
api.add_resource(StationParametersLevel, "/api/v1/station/<string:stationid>/parameters/level")
api.add_resource(StationParametersLevelUnit, "/api/v1/station/<string:stationid>/parameters/level/unit")
api.add_resource(StationParametersLevelDatetime, "/api/v1/station/<string:stationid>/parameters/level/datetime")
api.add_resource(StationParametersLevelValue, "/api/v1/station/<string:stationid>/parameters/level/value")
api.add_resource(StationParametersLevelPrevious24h, "/api/v1/station/<string:stationid>/parameters/level/previous24h")
api.add_resource(StationParametersLevelDelta24h, "/api/v1/station/<string:stationid>/parameters/level/delta24h")
api.add_resource(StationParametersLevelMax24h, "/api/v1/station/<string:stationid>/parameters/level/max24h")
api.add_resource(StationParametersLevelMean24h, "/api/v1/station/<string:stationid>/parameters/level/mean24h")
api.add_resource(StationParametersLevelMin24h, "/api/v1/station/<string:stationid>/parameters/level/min24h")
api.add_resource(StationParametersLevelMax1h, "/api/v1/station/<string:stationid>/parameters/level/max1h")
api.add_resource(StationParametersLevelMean1h, "/api/v1/station/<string:stationid>/parameters/level/mean1h")
api.add_resource(StationParametersLevelMin1h, "/api/v1/station/<string:stationid>/parameters/level/min1h")
api.add_resource(StationParametersDischarge, "/api/v1/station/<string:stationid>/parameters/discharge")
api.add_resource(StationParametersDischargeUnit, "/api/v1/station/<string:stationid>/parameters/discharge/unit")
api.add_resource(StationParametersDischargeDatetime, "/api/v1/station/<string:stationid>/parameters/discharge/datetime")
api.add_resource(StationParametersDischargeValue, "/api/v1/station/<string:stationid>/parameters/discharge/value")
api.add_resource(StationParametersDischargePrevious24h, "/api/v1/station/<string:stationid>/parameters/discharge/previous24h")
api.add_resource(StationParametersDischargeDelta24h, "/api/v1/station/<string:stationid>/parameters/discharge/delta24h")
api.add_resource(StationParametersDischargeMax24h, "/api/v1/station/<string:stationid>/parameters/discharge/max24h")
api.add_resource(StationParametersDischargeMean24h, "/api/v1/station/<string:stationid>/parameters/discharge/mean24h")
api.add_resource(StationParametersDischargeMin24h, "/api/v1/station/<string:stationid>/parameters/discharge/min24h")
api.add_resource(StationParametersDischargeMax1h, "/api/v1/station/<string:stationid>/parameters/discharge/max1h")
api.add_resource(StationParametersDischargeMean1h, "/api/v1/station/<string:stationid>/parameters/discharge/mean1h")
api.add_resource(StationParametersDischargeMin1h, "/api/v1/station/<string:stationid>/parameters/discharge/min1h")

if __name__ == "__main__":
    app.run('0.0.0.0', 8023, debug=True)
