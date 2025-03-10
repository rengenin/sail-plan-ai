from datetime import datetime, timedelta

import requests


def get_tidal_data(noaa_id: int, start_date: str, end_date: str = None):
    """
    NOAA Station Public API
    """
    noaa_root = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    converted_start_date = datetime.strptime(start_date, "%m/%d/%Y")
    if not end_date:
        converted_end_date = converted_start_date + timedelta(days=1)
    else:
        converted_end_date = datetime.strptime(end_date, "%m/%d/%Y")

    str_start_date = datetime.strftime(converted_start_date, "%Y%m%d")
    str_end_date = datetime.strftime(converted_end_date, "%Y%m%d")
    url = f"""{noaa_root}?product=predictions&station={
        noaa_id
    }&datum=MLLW&units=metric&time_zone=gmt&format=json&begin_date={
        str_start_date
    }&end_date={str_end_date}"""
    print("trying to pull NOAA data with the following URL")
    print(url)
    station_data = requests.get(url)
    if station_data.status_code == requests.codes.ok:
        return station_data.status_code, station_data.json()
    else:
        return station_data.status_code, {}
