import datetime
import json
import os
import tempfile

import openmeteo_requests
import pandas as pd
import requests_cache
from http.server import BaseHTTPRequestHandler
from retry_requests import retry


def load_itinerary():
    # Load from the root directory (one level up from api/)
    # In Vercel, the file is usually at the root of the task
    try:
        # Try local path first (relative to script)
        with open(
            os.path.join(os.path.dirname(__file__), "../itinerary.json"), "r"
        ) as f:
            data = json.load(f)
    except FileNotFoundError:
        # Fallback for Vercel environment where file might be in root
        with open("itinerary.json", "r") as f:
            data = json.load(f)

    # Convert date strings to datetime.date objects
    for city in data:
        city["dates"] = [datetime.date.fromisoformat(d) for d in city["dates"]]
    return data


def get_weather_data():
    CITIES = load_itinerary()

    # Use /tmp for cache in serverless environment (writable)
    cache_path = os.path.join(tempfile.gettempdir(), ".cache")
    cache_session = requests_cache.CachedSession(cache_path, expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo_client = openmeteo_requests.Client(session=retry_session)

    url = "https://api.open-meteo.com/v1/forecast"
    results = []

    for city in CITIES:
        params = {
            "latitude": city["latitude"],
            "longitude": city["longitude"],
            "hourly": "temperature_2m",
            "forecast_days": 16,
            "wind_speed_unit": "mph",
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "inch",
        }
        responses = openmeteo_client.weather_api(url, params=params)
        response = responses[0]

        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()

        hourly_data = {
            "date": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left",
            )
        }
        hourly_data["temperature_2m"] = hourly_temperature_2m

        df = pd.DataFrame(data=hourly_data)
        df["date_only"] = df["date"].dt.date

        for visit_date in city["dates"]:
            day_data = df[df["date_only"] == visit_date]
            max_temp = day_data["temperature_2m"].max()
            min_temp = day_data["temperature_2m"].min()
            results.append(
                {
                    "date": visit_date.isoformat(),
                    "city": city["name"],
                    "country": city["country"],
                    "max_temp": None
                    if pd.isna(max_temp)
                    else round(float(max_temp), 1),
                    "min_temp": None
                    if pd.isna(min_temp)
                    else round(float(min_temp), 1),
                }
            )

    results.sort(key=lambda x: x["date"])
    return results


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = get_weather_data()
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
        return
