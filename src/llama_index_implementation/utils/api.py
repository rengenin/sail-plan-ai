from geopy.geocoders import Nominatim
from typing import Optional
import diskcache as dc


cache = dc.Cache("./cache")

def get_lat_lon(location: str) -> Optional[tuple]:
    """Convert a location string into latitude and longitude using OpenStreetMap."""
    cache_key = f"geocode_{location}"
    
    if cache_key in cache:
        print("Returning cached geocode.")
        return cache[cache_key]
    
    geolocator = Nominatim(user_agent="geoapi")
    location_data = geolocator.geocode(location)
    
    if location_data:
        geocode = (location_data.latitude, location_data.longitude)
        cache.set(cache_key, geocode, expire=86400)  # Cache for 1 day
        return geocode
    else:
        print(f"Error: Could not geocode '{location}'")
        return None