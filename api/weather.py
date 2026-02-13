import datetime
import json

import openmeteo_requests
import pandas as pd
import requests_cache
from http.server import BaseHTTPRequestHandler
from retry_requests import retry

CITIES = [
    {
        "name": "Nashville",
        "country": "USA",
        "latitude": 36.1745,
        "longitude": -86.7680,
        "dates": [datetime.date(2026, 2, 18)],
    },
    {
        "name": "Barcelona",
        "country": "Spain",
        "latitude": 41.3902,
        "longitude": 2.154,
        "dates": [
            datetime.date(2026, 2, 19),
            datetime.date(2026, 2, 20),
            datetime.date(2026, 2, 21),
            datetime.date(2026, 2, 22),
            datetime.date(2026, 2, 23),
            datetime.date(2026, 3, 2),
        ],
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


def get_weather_data():
    cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
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
