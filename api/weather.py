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


def get_weather_description(code):
    """Convert WMO weather code to human-readable description."""
    mapping = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Dense drizzle",
        56: "Freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Rain",
        65: "Heavy rain",
        66: "Freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow",
        73: "Snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return mapping.get(code, "Unknown")


def get_worst_weather_code(codes):
    """Get the most significant weather code (worst-case)."""
    priority = {
        99: 10,  # Thunderstorm with heavy hail
        96: 9,  # Thunderstorm with slight hail
        95: 8,  # Thunderstorm
        82: 7,  # Violent rain showers
        81: 6,  # Rain showers
        80: 5,  # Slight rain showers
        67: 4,  # Heavy freezing rain
        66: 3,  # Freezing rain
        65: 2,  # Heavy rain
        63: 1,  # Rain
        61: 0,  # Slight rain
    }

    max_priority = -1
    worst_code = codes[0] if len(codes) > 0 else 0

    for code in codes:
        if code in priority and priority[code] > max_priority:
            max_priority = priority[code]
            worst_code = code

    return worst_code


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
            "hourly": "temperature_2m,weather_code",
            "forecast_days": 16,
            "wind_speed_unit": "mph",
            "temperature_unit": "fahrenheit",
            "precipitation_unit": "inch",
        }
        responses = openmeteo_client.weather_api(url, params=params)
        response = responses[0]

        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_weather_code = hourly.Variables(1).ValuesAsNumpy()

        hourly_data = {
            "date": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left",
            )
        }
        hourly_data["temperature_2m"] = hourly_temperature_2m
        hourly_data["weather_code"] = hourly_weather_code

        df = pd.DataFrame(data=hourly_data)
        df["date_only"] = df["date"].dt.date

        for visit_date in city["dates"]:
            day_data = df[df["date_only"] == visit_date]
            max_temp = day_data["temperature_2m"].max()
            min_temp = day_data["temperature_2m"].min()

            # Get worst-case weather code for the day
            weather_codes = day_data["weather_code"].dropna().astype(int).tolist()
            worst_code = (
                get_worst_weather_code(weather_codes) if weather_codes else None
            )
            weather_desc = (
                get_weather_description(worst_code) if worst_code is not None else None
            )

            results.append(
                {
                    "date": visit_date.isoformat(),
                    "city": city["name"],
                    "country": city["country"],
                    "max_temp": None
                    if pd.isna(max_temp)
                    else round(float(max_temp), 0),
                    "min_temp": None
                    if pd.isna(min_temp)
                    else round(float(min_temp), 0),
                    "weather": weather_desc,
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
