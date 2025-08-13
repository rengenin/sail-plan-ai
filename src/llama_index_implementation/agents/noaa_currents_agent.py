import requests
from typing import Dict, List
from geopy.distance import geodesic
from datetime import datetime, timedelta
from pydantic import BaseModel
import pandas as pd 
from llama_index.core import SummaryIndex, SimpleDirectoryReader, GPTVectorStoreIndex, Document
from llama_index.core.llms import ChatMessage
from llama_index.readers.web import SimpleWebPageReader
from bs4 import BeautifulSoup
import diskcache as dc 
import numpy as np

from utils import llm
from utils import api


cache = dc.Cache("./cache")


class NOAAStations(BaseModel):
    station_ids: List[str]
    station_names: List[str]
    station_distances: List[float]


def get_noaa_tide_stations():
    """Fetch NOAA station data and extract relevant details."""

    cache_key = "noaa_stations"

    if cache_key in cache:
        print("Returning cached NOAA tide stations.")
        return cache[cache_key]

    url = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        stations = data.get("stations", [])  # Extract station list
        print(stations)
        
        # Keep only relevant fields
        filtered_stations = [
            {
                "id": station["id"],
                "name": station["name"],
                "lat": station["lat"],
                "lon": station["lng"]
            }
            for station in stations
        ]
        
        cache.set(cache_key, filtered_stations, expire=86400)  # Cache for 1 day
        return filtered_stations
    else:
        print(f"Error fetching NOAA data: {response.status_code}")
        return None
    

def get_noaa_data(station_id: str, start_date: str, end_date: str = None):
    """Fetch tidal and current data from NOAA API with caching."""
    
    cache_key = f"noaa_data_{station_id}"
    
    # Check if data is in cache
    if cache_key in cache:
        print("Returning cached NOAA data.")
        return cache[cache_key]

    try:
        noaa_root = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?"

        # &product=currents_predictions&time_zone=lst&interval=MAX_SLACK&units=english&application=DataAPI_Sample&format=xml&bin=1
        converted_start_date = datetime.strptime(start_date, "%m/%d/%Y")
        if not end_date:
            converted_end_date = converted_start_date + timedelta(days=1)
        else:
            converted_end_date = datetime.strptime(end_date, "%m/%d/%Y")

        str_start_date = datetime.strftime(converted_start_date, "%Y%m%d")
        str_end_date = datetime.strftime(converted_end_date, "%Y%m%d")
        # Original
        # url = f"""{noaa_root}product=predictions&station={
        #     station_id
        # }&datum=MLLW&units=english&time_zone=lst&format=json&begin_date={
        #     str_start_date
        # }&end_date={str_end_date}"""

        url = f"""{noaa_root}product=predictions&station={
            station_id
        }&datum=MLLW&units=english&time_zone=lst&interval=hilo&format=json&begin_date={
            str_start_date
        }&end_date={str_end_date}"""

        print("NOAA URL")
        print(url)
        print(100*"_--")

        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        tide_info = data["predictions"]

        # Store data in cache with a 1-hour expiration
        cache.set(cache_key, tide_info, expire=3600)

        return tide_info
    except Exception as e:
        print(f"Error fetching NOAA tidal data: {e}")
        return {}


def get_nearest_stations(user_location, stations, max_results=15):
    """Find the closest NOAA stations to a given location."""
    user_lat, user_lon = user_location
    # Compute distances
    stations_with_distance = [
        {
            **station,
            "distance": geodesic((user_lat, user_lon), (station["lat"], station["lon"])).miles
        }
        for station in stations
    ]

    # Sort by closest distance
    sorted_stations = sorted(stations_with_distance, key=lambda x: x["distance"])

    return sorted_stations#[:max_results]  # Keep only the closest stations


def get_noaa_current_stations(lat_lon):

    cache_key = "noaa_current_stations"
    if cache_key in cache:
        print("Returning cached NOAA currents stations.")
        return cache[cache_key]
    
    # Not measuring distance well
    station_table = pd.read_csv("data/current_stations.csv")
    station_table["lon"] = station_table["lon"] * -1
    print(100*"=")
    print(station_table)
    closest_station = get_nearest_stations(lat_lon, station_table.to_dict(orient='records'))

    # print(closest_station)
    """
    not calculating correct distances
    Convert the latitude and longitude of your location and each station from degrees to radians.
    """
    df = pd.DataFrame(closest_station).sort_values(by="distance").head()

    # Convert df to llamaindex document
    documents = [
        Document(text=row.to_string(), metadata={"index": idx}) 
        for idx, row in df.iterrows()
    ]

    # print(df[df["name"].str.contains("Rich")])
    

    # reader = SimpleDirectoryReader(
    #     input_files=["data/current_stations.tsv"]
    # )
    # station_table = reader.load_data()


    # documents = SimpleWebPageReader(html_to_text=True).load_data(
    #     ["https://tidesandcurrents.noaa.gov/noaacurrents/stations.html?g=698"]
    # )
    # print(documents)

    # return documents
    # open_ai_llm = llm.get_model()

    # input_text = f"""
    #             I am going to provide you with a specific document of data.
    #             The document contains a dataset of current stations, primarily focused on various locations in the Pacific Northwest, particularly around Washington State. Each entry includes the name of the station, its geographical coordinates (latitude and longitude), depth, and a classification (e.g., Subordinate, Harmonic, Weak and Variable).

    #             Key details include:
    #             - The dataset is in CSV format and has a file size of 36,285 bytes.
    #             - The entries cover a wide range of locations, including Sand Island Tower, Baker Bay entrance, and various points along the coast and waterways.
    #             - Depths range from shallow (e.g., 5ft) to deep (e.g., 297ft).
    #             - The classification indicates the nature of the station's signal or data reliability.

    #             Overall, the dataset serves as a resource for understanding maritime navigation and environmental monitoring in the region.

    #             Here is the document: {station_table}

    #             I am located at {lat_lon}.

    #             What station is closest to me?
    #             """
    # input_text = f"""
    #             You are a maritime data engineer with practice doing geographic measurements. 
    #             You are provided a target location in LAT/LON as well as a table of NOAA station with their respective LAT/LON
    #             positions. You must find the closest station based on geocode relative to target position. Find the station in 
    #             tabular data that has the shortest haversine distance from the target position and return it.

    #             - Target Position: {lat_lon}
    #             - Table of NOAA stations: {station_table}

    #             Return the closest station as a JSON with the following schema:
    #             # ## **Example Output Format**
    #             {{
    #                 "NAME": str,
    #                 "ID": str,
    #                 "BIN#": int,
    #                 "LAT": str,
    #                 "LON": str,
    #                 "PREDICTIONS": str
    #             }}
    #             """
    # input_text = f"""
    # You are a maritime data engineer. Your job is to extract tabular data from NOAA webpages
    # turn them into JSON data.

    # NOAA Current Predictions:
    # - Current Prediction Stations: {documents}

    # Your task:
    # - Identify the columns and rows of table
    # - Extract tabular data into JSON

    # ## *Table Schema**
    # 1. NAME: str
    # 2. ID: str
    # 3. BIN#: int
    # 4. LAT: str
    # 5. LON: str
    # 6. PREDICTIONS: str


    # ## **Example Output Format**
    # {{
    #     "NAME": List[str],
    #     "ID": List[str],
    #     "BIN#": List[int],
    #     "LAT": List[str],
    #     "LON": List[str],
    #     "PREDICTIONS": List[str]
    # }}
    # """

    # open_ai_llm = llm.get_model()
    # messages = [ChatMessage(role="system", content=input_text)]
    # # return llm.call_llm(messages, open_ai, NOAAStations)

    # response = open_ai_llm.chat(messages)
    # print(response)
    # messages = [ChatMessage(role="system", content=input_text)]
    

# def currents_agent(location: str, start_date: str):

# def 


def tides_and_currents(location: str, start_date:str ):
    lat_lon = api.get_lat_lon(location)

    if not lat_lon:
        print("Failed to get geocode. Exiting.")
        return
    
    # working here
    current_stations = get_noaa_current_stations(lat_lon)


    # stations = get_noaa_tide_stations()
    # print(stations)
    # if not stations:
    #     print("Failed to fetch NOAA data. Exiting.")
    #     return

    # closest_stations = get_nearest_stations(lat_lon, stations)
    # for station in closest_stations:
    #     print(f"Fetching tides data for station: {station['name']}")
    #     tides_data = get_noaa_data(station["id"], start_date=start_date)
    #     if tides_data:
    #         break
    
    # input_text = f"""
    # You are a maritime data analyst. Your job is to analyze the provided tidal data and extract key insights.

    # NOAA Tidal Data:
    # - Tide Predictions: {tides_data}

    # Your task:
    # - Identify the **maximum ebb tide** (strongest outgoing current) and its rate in knots.
    # - Identify the **maximum flood tide** (strongest incoming current) and its rate in knots.
    # - Find all **slack tide times** (when current speed is near zero, between transitions).
    
    # ## **Rules for Analysis**
    # 1. Max ebb occurs when the lowest tide level is reached before reversing.
    # 2. Max flood occurs when the highest tide level is reached before reversing.
    # 3. Slack tide happens at transition points, when tide stops before changing direction.
    # 4. Return **only** JSON output, with NO additional explanation.



    # ## **Example Output Format**
    # {{
    #     "max_ebb_time": "HH:MM",
    #     "max_ebb_rate": "X.XX knots",
    #     "max_flood_time": "HH:MM",
    #     "max_flood_rate": "X.XX knots",
    #     "slack_tide_times": ["HH:MM", "HH:MM"]
    # }}
    # """

    # open_ai_llm = llm.get_model()
    # messages = [ChatMessage(role="system", content=input_text)]
    # # return llm.call_llm(messages, open_ai, NOAAStations)
    # try:
    #     response = open_ai_llm.chat(messages)
    #     print(100*"=")
    #     print(response)
    #     print(100*"=")
    #     return response
    # except Exception as e:
    #     print(f"Error in decision making: {e}")
    #     return None