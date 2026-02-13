import datetime

import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry

CITIES = [
    {
        "name": "Nashville",
        "country": "USA",
        "latitude": 36.1745,
        "longitude": -86.7680,
        "dates": [datetime.date(2026, 2, 19)],
    },
    {
        "name": "Barcelona",
        "country": "Spain",
        "latitude": 41.3902,
        "longitude": 2.154,
        "dates": [
            datetime.date(2026, 2, 20),
            datetime.date(2026, 2, 21),
            datetime.date(2026, 2, 22),
            datetime.date(2026, 2, 23),
            datetime.date(2026, 3, 2),
        ],
    },
    {
        "name": "Balearic Sea",
        "country": "Spain",
        "latitude": 40.8,
        "longitude": 2.4,
        "dates": [datetime.date(2026, 2, 24)],
    },
    {
        "name": "La Goulette",
        "country": "Tunisia",
        "latitude": 36.8196,
        "longitude": 10.3035,
        "dates": [datetime.date(2026, 2, 25)],
    },
    {
        "name": "Palermo",
        "country": "Italy",
        "latitude": 38.1167,
        "longitude": 13.3667,
        "dates": [datetime.date(2026, 2, 26)],
    },
    {
        "name": "Rome",
        "country": "Italy",
        "latitude": 41.9028,
        "longitude": 12.4964,
        "dates": [datetime.date(2026, 2, 27)],
    },
    {
        "name": "Savona",
        "country": "Italy",
        "latitude": 44.3,
        "longitude": 8.4833,
        "dates": [datetime.date(2026, 2, 28)],
    },
    {
        "name": "Marseille",
        "country": "France",
        "latitude": 43.2964,
        "longitude": 5.37,
        "dates": [datetime.date(2026, 3, 1)],
    },
    {
        "name": "Paris",
        "country": "France",
        "latitude": 48.8647,
        "longitude": 2.349,
        "dates": [
            datetime.date(2026, 3, 3),
            datetime.date(2026, 3, 4),
            datetime.date(2026, 3, 5),
            datetime.date(2026, 3, 6),
        ],
    },
]

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
