import os
import json
import requests
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from llama_index.core.llms import ChatMessage
from llama_index.llms.openai import OpenAI
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# NOAA API URL
NOAA_STATION_API = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json"


### ✅ 1. Get Latitude/Longitude from Location
def get_lat_lon(location: str) -> Optional[tuple]:
    """Convert a location string into latitude and longitude using OpenStreetMap."""
    geolocator = Nominatim(user_agent="geoapi")
    location_data = geolocator.geocode(location)
    
    if location_data:
        return location_data.latitude, location_data.longitude
    else:
        print(f"Error: Could not geocode '{location}'")
        return None


### ✅ 2. Fetch NOAA Stations
def get_noaa_stations():
    """Fetch NOAA station data and extract relevant details."""
    response = requests.get(NOAA_STATION_API)
    
    if response.status_code == 200:
        data = response.json()
        stations = data.get("stations", [])  # Extract station list
        
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
        
        return filtered_stations
    else:
        print(f"Error fetching NOAA data: {response.status_code}")
        return None


### ✅ 3. Filter Closest NOAA Stations
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

    return sorted_stations[:max_results]  # Keep only the closest stations


### ✅ 4. Initialize LLM
def get_model() -> Optional[OpenAI]:
    """Initialize OpenAI LLM with API Key."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("API Key Error: Please set OPENAI_API_KEY in your .env file.")
        raise ValueError("OpenAI API key not found.")
    return OpenAI(model="gpt-4o-mini", api_key=api_key)


### ✅ 5. LLM Structuring
class NOAAStations(BaseModel):
    station_ids: List[str]
    station_names: List[str]
    station_distances: List[float]


### ✅ 6. Run Full Pipeline
def main():
    # Step 1: Get Geocode
    location = "Port Orchard Marina, Port Orchard, Washington"
    lat_lon = get_lat_lon(location)

    if not lat_lon:
        print("Failed to get geocode. Exiting.")
        return

    # Step 2: Fetch NOAA Stations
    stations = get_noaa_stations()
    if not stations:
        print("Failed to fetch NOAA data. Exiting.")
        return

    # Step 3: Get Nearest Stations
    closest_stations = get_nearest_stations(lat_lon, stations)

    # Step 4: Format for LLM
    stations_text = "\n".join(
        [f"{s['id']} - {s['name']} ({s['distance']:.1f} miles)" for s in closest_stations]
    )

    # Step 5: Call LLM
    llm = get_model()
    messages = [
        ChatMessage(
            role="system",
            content=f"""Here is a list of NOAA water level stations near {location}:
            {stations_text}

            Find the 8 closest stations and return them in this JSON format:
            {{
                "station_ids": List[str],
                "station_names": List[str],
                "station_distances": List[float]  # Distance in miles
            }}
            """,
        ),
    ]

    try:
        resp = llm.as_structured_llm(output_cls=NOAAStations).chat(messages)
        print(resp)
    except Exception as e:
        print(f"Error in LLM response: {e}")


if __name__ == "__main__":
    main()


#####################
### WEATHER AGENT ###
#####################

import os
import requests
from geopy.geocoders import Nominatim
from llama_index.core.llms import ChatMessage
from llama_index.llms.openai import OpenAI
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


### ✅ 1. Get Latitude/Longitude from Location
def get_lat_lon(location: str) -> Optional[tuple]:
    """Convert a location string into latitude and longitude using OpenStreetMap."""
    geolocator = Nominatim(user_agent="geoapi")
    location_data = geolocator.geocode(location)
    
    if location_data:
        return location_data.latitude, location_data.longitude
    else:
        print(f"Error: Could not geocode '{location}'")
        return None


### ✅ 2. Get NOAA Weather Forecast
def get_noaa_weather(lat, lon):
    """Fetch weather forecast from NOAA Weather API."""
    try:
        # Get NOAA forecast office & grid data
        url = f"https://api.weather.gov/points/{lat},{lon}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Extract forecast URL
        forecast_url = data["properties"]["forecast"]
        
        # Get the actual weather forecast
        forecast_response = requests.get(forecast_url)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()
        
        # Extract relevant forecast details
        periods = forecast_data["properties"]["periods"][:3]  # Next 3 periods
        weather_info = [
            {
                "name": p["name"],
                "temperature": p["temperature"],
                "unit": p["temperatureUnit"],
                "wind": p["windSpeed"],
                "wind_direction": p["windDirection"],
                "short_forecast": p["shortForecast"]
            }
            for p in periods
        ]
        
        return weather_info
    
    except Exception as e:
        print(f"Error fetching NOAA weather data: {e}")
        return None


### ✅ 3. Define Weather Data Model
class WeatherForecast(BaseModel):
    name: List[str]  # Time period (e.g., "Tonight", "Monday")
    temperature: List[int]  # Temp values
    unit: str  # Unit (e.g., "F")
    wind: List[str]  # Wind speed (e.g., "10 mph")
    wind_direction: List[str]  # Wind direction (e.g., "NW")
    short_forecast: List[str]  # Summary (e.g., "Partly Cloudy")


### ✅ 4. Initialize LLM
def get_model() -> Optional[OpenAI]:
    """Initialize OpenAI LLM with API Key."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("API Key Error: Please set OPENAI_API_KEY in your .env file.")
        raise ValueError("OpenAI API key not found.")
    return OpenAI(model="gpt-4o-mini", api_key=api_key)


### ✅ 5. Run WeatherAgent
def main():
    location = "Port Orchard Marina, Port Orchard, Washington"
    lat_lon = get_lat_lon(location)

    if not lat_lon:
        print("Failed to get geocode. Exiting.")
        return

    # Get NOAA Weather
    weather_data = get_noaa_weather(lat_lon[0], lat_lon[1])
    if not weather_data:
        print("Failed to fetch NOAA weather data. Exiting.")
        return

    # Format for LLM
    weather_text = "\n".join(
        [f"{w['name']}: {w['temperature']}°{w['unit']}, {w['wind']} winds from {w['wind_direction']}, {w['short_forecast']}" 
         for w in weather_data]
    )

    # Call LLM
    llm = get_model()
    messages = [
        ChatMessage(
            role="system",
            content=f"""Here is the NOAA weather forecast for {location}:
            {weather_text}

            Return the forecast in this JSON format:
            {{
                "name": List[str],  # Time period
                "temperature": List[int],  # Temperature values
                "unit": str,  # Temperature unit
                "wind": List[str],  # Wind speed
                "wind_direction": List[str],  # Wind direction
                "short_forecast": List[str]  # Weather summary
            }}
            """,
        ),
    ]

    try:
        resp = llm.as_structured_llm(output_cls=WeatherForecast).chat(messages)
        print(resp)
    except Exception as e:
        print(f"Error in LLM response: {e}")


if __name__ == "__main__":
    main()

###################
## CAPTAIN AGENT ##
###################

import json
from typing import Dict
from llama_index.core.llms import ChatMessage
from llama_index.llms.openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


### ✅ 1. Simulated Data Retrieval
def get_noaa_data() -> Dict:
    """Simulate getting NOAA tidal and current data."""
    return {
        "wave_height": 2.5,  # in feet
        "current_speed": 1.2,  # in knots
    }


def get_weather_data() -> Dict:
    """Simulate getting NOAA weather forecast data."""
    return {
        "wind_speed": "12 mph",
        "wind_direction": "NW",
        "short_forecast": "Partly Cloudy",
        "temperature": 68,  # Fahrenheit
    }


### ✅ 2. Initialize LLM
def get_model() -> OpenAI:
    """Initialize OpenAI model for decision making."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not found.")
    return OpenAI(model="gpt-4o-mini", api_key=api_key)


### ✅ 3. Define Decision Function
def captain_decision():
    """Decides if it's safe to sail based on NOAA & weather data."""
    
    # Fetch data from agents
    noaa_data = get_noaa_data()
    weather_data = get_weather_data()

    # Format data for LLM
    input_text = f"""
    NOAA Tidal Data:
    - Wave Height: {noaa_data["wave_height"]} ft
    - Current Speed: {noaa_data["current_speed"]} knots

    Weather Forecast:
    - Wind: {weather_data["wind_speed"]} from {weather_data["wind_direction"]}
    - Temperature: {weather_data["temperature"]}°F
    - Forecast: {weather_data["short_forecast"]}

    Based on this data, determine if it's **safe to sail**. Use these rules:
    - Wind: Safe (5-15 mph), Caution (16-25 mph), Unsafe (>25 mph)
    - Wave Height: Safe (<3 ft), Caution (3-5 ft), Unsafe (>5 ft)
    - Forecast: Safe (Clear, Partly Cloudy), Caution (Showers, Overcast), Unsafe (Storms, High Winds)

    Return in JSON format:
    {{
        "decision": str,  # "Safe", "Caution", or "Unsafe"
        "reason": str  # Explanation of decision
    }}
    """

    # Call LLM
    llm = get_model()
    messages = [ChatMessage(role="system", content=input_text)]

    try:
        response = llm.chat(messages)
        print(response)
        return response
    except Exception as e:
        print(f"Error in decision making: {e}")
        return None


### ✅ 4. Run CaptainAgent
if __name__ == "__main__":
    captain_decision()

######################
## IMPROVED VERSION ##
######################
import json
import os
from typing import Dict
import requests
from llama_index.core.llms import ChatMessage
from llama_index.llms.openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

### ✅ 1. Get Real Data from NOAAAgent
def get_noaa_data(station_id: str) -> Dict:
    """Fetch tides and current data from NOAAAgent."""
    try:
        url = f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=predictions&datum=MLLW&station={station_id}&time_zone=lst_ldt&units=english&interval=hilo&format=json"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Extract tide cycle (last and next high/low tide)
        tide_predictions = data["predictions"]
        tide_info = {
            "last_tide": tide_predictions[0],  # Most recent tide
            "next_tide": tide_predictions[1],  # Upcoming tide
        }
        return tide_info

    except Exception as e:
        print(f"Error fetching NOAA tidal data: {e}")
        return None


### ✅ 2. Get Real Data from WeatherAgent
def get_weather_data(lat: float, lon: float) -> Dict:
    """Fetch weather forecast from NOAA Weather API."""
    try:
        url = f"https://api.weather.gov/points/{lat},{lon}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Extract forecast URL
        forecast_url = data["properties"]["forecast"]

        # Get the actual forecast
        forecast_response = requests.get(forecast_url)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()

        # Extract relevant forecast details (next 12 hours)
        periods = forecast_data["properties"]["periods"][:2]
        weather_info = {
            "wind_speed": periods[0]["windSpeed"],
            "wind_direction": periods[0]["windDirection"],
            "short_forecast": periods[0]["shortForecast"],
            "temperature": periods[0]["temperature"],
        }

        return weather_info

    except Exception as e:
        print(f"Error fetching NOAA weather data: {e}")
        return None


### ✅ 3. Initialize LLM
def get_model() -> OpenAI:
    """Initialize OpenAI model for decision making."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key not found.")
    return OpenAI(model="gpt-4o-mini", api_key=api_key)


### ✅ 4. Define Captain Decision Function
def captain_decision(station_id: str, lat: float, lon: float):
    """Decides if it's safe to sail based on real NOAA & weather data."""
    
    # Get real data
    noaa_data = get_noaa_data(station_id)
    weather_data = get_weather_data(lat, lon)

    if not noaa_data or not weather_data:
        print("Error fetching data. Cannot make decision.")
        return None

    # Extract tide cycle info
    last_tide_type = noaa_data["last_tide"]["type"]
    next_tide_type = noaa_data["next_tide"]["type"]

    # Categorize tide safety
    if last_tide_type == "H" and next_tide_type == "L":
        tide_safety = "Caution (Falling tide)"
    elif last_tide_type == "L" and next_tide_type == "H":
        tide_safety = "Favorable (Rising tide)"
    elif last_tide_type == "H" and next_tide_type == "H":
        tide_safety = "Favorable (High tide)"
    else:
        tide_safety = "Unsafe (Low tide)"

    # Format data for LLM
    input_text = f"""
    NOAA Tidal Data:
    - Last Tide: {last_tide_type}
    - Next Tide: {next_tide_type}
    - Tide Safety: {tide_safety}

    Weather Forecast:
    - Wind: {weather_data["wind_speed"]} from {weather_data["wind_direction"]}
    - Temperature: {weather_data["temperature"]}°F
    - Forecast: {weather_data["short_forecast"]}

    Sailing Safety Rules:
    - Wind: Safe (5-15 mph), Caution (16-25 mph), Unsafe (>25 mph)
    - Tide: Favorable (Rising/High Tide), Caution (Falling Tide), Unsafe (Low Tide)
    - Forecast: Safe (Clear, Partly Cloudy), Caution (Showers, Overcast), Unsafe (Storms, High Winds)

    Return decision in JSON:
    {{
        "decision": str,  # "Safe", "Caution", or "Unsafe"
        "reason": str  # Explanation of decision
    }}
    """

    # Call LLM
    llm = get_model()
    messages = [ChatMessage(role="system", content=input_text)]

    try:
        response = llm.chat(messages)
        print(response)
        return response
    except Exception as e:
        print(f"Error in decision making: {e}")
        return None


### ✅ 5. Run CaptainAgent
if __name__ == "__main__":
    station_id = "9445958"  # Example: Port Orchard, WA
    lat, lon = 47.5404, -122.6361  # Example coordinates

    captain_decision(station_id, lat, lon)


