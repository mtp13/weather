import datetime
import json
import os

import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry


def load_itinerary():
    with open("itinerary.json", "r") as f:
        data = json.load(f)

    # Convert date strings to datetime.date objects
    for city in data:
        city["dates"] = [datetime.date.fromisoformat(d) for d in city["dates"]]
    return data


CITIES = load_itinerary()

cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

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
    responses = openmeteo.weather_api(url, params=params)
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
                "date": visit_date,
                "city": city["name"],
                "country": city["country"],
                "max_temp": max_temp,
                "min_temp": min_temp,
            }
        )

results.sort(key=lambda x: x["date"])

for r in results:
    if pd.isna(r["max_temp"]) or pd.isna(r["min_temp"]):
        print(f"{r['city']} ({r['date'].strftime('%b %d')}): Unavailable")
    else:
        print(
            f"{r['city']} ({r['date'].strftime('%b %d')}): High: {r['max_temp']:.1f}°F, Low: {r['min_temp']:.1f}°F"
        )
