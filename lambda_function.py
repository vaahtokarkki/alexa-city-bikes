import os
import json

from urllib import request, error
from geopy.geocoders import Nominatim
from geopy import distance
from graphqlclient import GraphQLClient


CARD_TITLE = "City bikes"


def lambda_handler(event, context):
    print("got event", event)

    if (event["session"]["application"]["applicationId"] !=
            os.environ["ALEXA_APPLICATION_ID"]):
        raise ValueError("Invalid Application ID")

    if event["request"]["type"] == "IntentRequest":
        return on_intent(event)

    return main_handler(event)


def main_handler(event):
    """
    Get nearest stations and create speech for it.
    More stations added to session attrubutes for accessing them later
    """

    address = ""
    try:
        address = get_address(event)
    except ValueError:
        # Value error is raised if no permissions to address
        return ask_permissions()
    except Exception:
        # Some other error when getting location
        speech_output = "Sorry, error occurred when retrieving device address."
        resp = build_speechlet_response(CARD_TITLE, speech_output, True)
        return build_response(resp)

    nearest_stations = get_nearest_stations(3, address)
    station = nearest_stations[0]

    speech_output = f"On station {station['name']} is {station['bikesAvailable']} " \
        "bikes available. Do you want to hear more nearby stations?"

    session_attributes = {
        "previousIntent": "mainHandler",
        "nextStations": build_next_stations(nearest_stations[1:3])
    }

    response = build_speechlet_response(CARD_TITLE, speech_output, False)
    return build_response(response, session_attributes)


def get_address(event):
    access_token = event["context"]["System"]["apiAccessToken"]
    api_end_point = event["context"]["System"]["apiEndpoint"]
    device_id = event["context"]["System"]["device"]["deviceId"]

    req = request.Request(
        f'{api_end_point}/v1/devices/{device_id}/settings/address'
    )
    req.add_header("Authorization", f"Bearer {access_token}")

    try:
        resp = request.urlopen(req)
        data = json.loads(resp.read().decode('utf8'))
    except error.HTTPError as e:
        print("got status code error", str(e))
        if e.status == 403:
            raise ValueError()
        raise RuntimeError()
    except error.URLError as e:
        print("got url error", str(e))
        raise RuntimeError()

    address = data["addressLine1"]
    city = data["city"]
    country = data["countryCode"]
    return f"{address}, {city} {country}"


def get_nearest_stations(limit, address):
    stations = get_bike_stations()
    device_location = geocode_address(address)
    stations = sort_bike_stations(stations, device_location)
    return stations[:limit]


def geocode_address(address):
    geolocator = Nominatim(user_agent="Amazon Alexa")
    try:
        location = geolocator.geocode(address)
        return (location.latitude, location.longitude)
    except:
        return None


def get_bike_stations():
    client = GraphQLClient(
        'https://api.digitransit.fi/routing/v1/routers/hsl/index/graphql'
    )

    result = client.execute('''
    {
    bikeRentalStations {
        name
        stationId
        bikesAvailable
        lat
        lon
    }
    }
    ''')

    stations = json.loads(result)
    return stations["data"]["bikeRentalStations"]


def sort_bike_stations(bike_stations, location):
    """
    bike_stations contains array of station objects
    {name, stationId, bikesAvailable, lat, lon}
    """

    stations = bike_stations.copy()

    for index, station in enumerate(stations):
        station_location = (station["lat"], station["lon"])
        dist = distance.distance(station_location, location).m
        stations[index]["distance"] = dist

    stations = sorted(stations, key=lambda station: station["distance"])
    stations = list(filter(lambda station: station["bikesAvailable"] > 0, stations))

    return stations


def build_next_stations(stations):
    """
    Build speech for yes intent, takes array of two next stations.
    By default after this speech session is ended.
    """

    station_0_bikes = stations[0]['bikesAvailable']
    station_1_bikes = stations[1]['bikesAvailable']

    return f"On station {stations[0]['name']} is {station_0_bikes} " \
        f"bike{'s' if station_0_bikes > 1 else ''} available and on station" \
        f"{stations[1]['name']} is {station_1_bikes} " \
        f"bike{'s' if station_1_bikes > 1 else ''} available. Goodbye and happy cycling!"


def on_intent(event):
    """ Return speech output based on intent """

    intent = event["request"]["intent"]["name"]

    if intent in ("AMAZON.CancelIntent", "AMAZON.StopIntent", "AMAZON.NoIntent"):
        return handle_session_end_request()

    if intent == "AMAZON.YesIntent":
        if "attributes" in event["session"] and "previousIntent" in \
                event["session"]["attributes"]:

            if event["session"]["attributes"]["previousIntent"] == "AMAZON.HelpIntent":
                return main_handler(event)

            speech_output = event["session"]["attributes"]["nextStations"]
            resp = build_speechlet_response(CARD_TITLE, speech_output, True)
            return build_response(resp)

        speech_output = "Sorry, something went wrong."
        resp = build_speechlet_response(CARD_TITLE, speech_output, True)
        return build_response(resp)

    if intent == "isBikesAvailable":
        return main_handler(event)

    if intent == "AMAZON.HelpIntent":
        return handle_help_intent()

    speech_output = "Sorry, I don\'t know that."
    resp = build_speechlet_response(CARD_TITLE, speech_output, True)
    return build_response(resp)


def handle_session_end_request():
    speech_output = "Okay, goodbye and happy cycling!"
    resp = build_speechlet_response(CARD_TITLE, speech_output, True)
    return build_response(resp)


def build_speechlet_response(title, output, should_end_session):
    return {
        "outputSpeech": {
            "type": "PlainText",
            "text": output
        },
        "card": {
            "type": "Simple",
            "title": title,
            "content": output
        },
        "shouldEndSession": should_end_session
    }


def build_response(speechlet_response, session_attributes={}):
    return {
        "version": "1.0",
        "response": speechlet_response,
        "sessionAttributes": session_attributes
    }


def ask_permissions():
    response = {
        "outputSpeech": {
            "type": "PlainText",
            "text": ("Please check permissions and allow city bikes " +
                     "skill access to address. I sent a card for " +
                     "you to update skill settings.")
        },
        "card": {
            "type": "AskForPermissionsConsent",
            "permissions": [
                "read::alexa:device:all:address"
            ]
        },
        "shouldEndSession": False
    }
    return build_response(response)


def handle_help_intent():
    response = {
        "outputSpeech": {
            "type": "PlainText",
            "text": ("With this skill you can find closest city bike stations for you." +
                     " Use phrases open city bikes or ask city bikes is there " +
                     "bikes nearby. Do you want to find closest station for you?")
        },
        "card": {
            "type": "Simple",
            "title": "City bikes skill",
            "content": ("With this skill you can find closest city bike stations " +
                        "for you. Use phrases open city bikes or ask city bikes " +
                        "is there bikes nearby.")
        },
        "shouldEndSession": False
    }

    session_attributes = {
        "previousIntent": "AMAZON.HelpIntent"
    }

    return build_response(response, session_attributes)
