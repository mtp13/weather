"""Vercel Python function: the forecast for each day of the trip in itinerary.json.

One request to Open-Meteo's daily forecast covers every city. With timezone=auto,
Open-Meteo returns each city's days in that city's local time, so the highs, lows
and weather codes belong to the local calendar day. Only the standard library is
used, so the function has no runtime dependencies.
"""

import json
import math
import sys
import traceback
from datetime import UTC, date, datetime, timedelta
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_DAYS = 16  # The free API's limit
TIMEOUT_SECONDS = 10
ITINERARY_FILE = Path(__file__).resolve().parent.parent / "itinerary.json"
CACHE_CONTROL = "public, s-maxage=1800, stale-while-revalidate=3600"

# WMO weather codes, as used by Open-Meteo.
WEATHER_DESCRIPTIONS = {
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


class ForecastError(Exception):
    """Open-Meteo could not be reached or returned something unusable."""


def load_itinerary(path=ITINERARY_FILE):
    """Read the itinerary, turning each ISO date string into a date"""
    path = Path(path)
    if not path.exists():
        # Fallback in case the deployment runs from the project root.
        path = Path.cwd() / path.name
    with open(path) as f:
        cities = json.load(f)
    for city in cities:
        city["dates"] = [date.fromisoformat(d) for d in city["dates"]]
    return cities


def get_weather_description(code):
    """Describe a WMO weather code. None stays None and unknown codes give "Unknown"."""
    if code is None:
        return None
    return WEATHER_DESCRIPTIONS.get(code, "Unknown")


def round_temp(value):
    """Round a temperature half up to a whole degree (Python's round() is half-even)"""
    return math.floor(value + 0.5)


def forecast_url(cities):
    """Build one Open-Meteo daily-forecast URL that covers every city"""
    params = {
        "latitude": ",".join(str(city["latitude"]) for city in cities),
        "longitude": ",".join(str(city["longitude"]) for city in cities),
        "daily": "temperature_2m_max,temperature_2m_min,weather_code",
        "timezone": "auto",
        "temperature_unit": "fahrenheit",
        "forecast_days": FORECAST_DAYS,
    }
    return f"{FORECAST_URL}?{urlencode(params)}"


def urlopen_json(url):
    """GET a URL and decode the JSON body"""
    with urlopen(url, timeout=TIMEOUT_SECONDS) as response:
        return json.load(response)


def fetch_forecasts(cities, fetch=urlopen_json):
    """Fetch every city's daily forecast in one request, retrying a network error once.

    Returns one forecast dict per city, in itinerary order.
    """
    url = forecast_url(cities)
    for attempt in range(2):
        try:
            data = fetch(url)
            break
        except HTTPError as error:
            # Open-Meteo answers bad parameters with 400; retrying won't help.
            if error.code < 500 or attempt == 1:
                raise ForecastError(f"Open-Meteo returned HTTP {error.code}") from error
        except (URLError, TimeoutError, OSError) as error:
            if attempt == 1:
                raise ForecastError(f"Could not reach Open-Meteo: {error}") from error

    # One location comes back as an object, several as a list.
    if isinstance(data, dict):
        if data.get("error"):
            raise ForecastError(f"Open-Meteo error: {data.get('reason')}")
        data = [data]
    if not isinstance(data, list) or len(data) != len(cities):
        raise ForecastError("Open-Meteo returned an unexpected response")
    return data


def build_results(itinerary, forecasts, now):
    """Pair each itinerary date with its forecast day. Pure: `now` is an aware datetime.

    Each result has a status:
    - "ok": the date is in the forecast, with whole-degree temperatures
    - "past": the date is before today in that city's own timezone
    - "out_of_range": the date is beyond the forecast window
    """
    results = []
    for city, forecast in zip(itinerary, forecasts, strict=True):
        offset = timedelta(seconds=forecast.get("utc_offset_seconds", 0))
        local_today = (now.astimezone(UTC) + offset).date()
        daily = forecast["daily"]
        day_index = {day: i for i, day in enumerate(daily["time"])}

        for visit_date in city["dates"]:
            result = {
                "date": visit_date.isoformat(),
                "city": city["name"],
                "country": city["country"],
                "max_temp": None,
                "min_temp": None,
                "weather": None,
                "status": "out_of_range",
            }
            i = day_index.get(visit_date.isoformat())
            if visit_date < local_today:
                result["status"] = "past"
            elif i is not None:
                high = daily["temperature_2m_max"][i]
                low = daily["temperature_2m_min"][i]
                # The last forecast day can be null; treat it as not yet available.
                if high is not None and low is not None:
                    result.update(
                        max_temp=round_temp(high),
                        min_temp=round_temp(low),
                        weather=get_weather_description(daily["weather_code"][i]),
                        status="ok",
                    )
            results.append(result)

    results.sort(key=lambda result: result["date"])
    return results


def build_response(fetch=urlopen_json, itinerary_path=ITINERARY_FILE, now=None):
    """Return (status code, headers, body bytes) for GET /api/weather"""
    try:
        itinerary = load_itinerary(itinerary_path)
        forecasts = fetch_forecasts(itinerary, fetch=fetch) if itinerary else []
        results = build_results(itinerary, forecasts, now or datetime.now(UTC))
    except ForecastError as error:
        print(f"weather: {error}", file=sys.stderr)
        return _json_response(502, {"error": "The weather service is unavailable."})
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return _json_response(500, {"error": "Something went wrong."})
    return _json_response(200, results, cache_control=CACHE_CONTROL)


def _json_response(status, payload, cache_control="no-store"):
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": cache_control,
    }
    return status, headers, body


class handler(BaseHTTPRequestHandler):
    """Vercel's entry point for /api/weather"""

    def do_GET(self):
        # Look these up at call time so tests can monkeypatch them.
        status, headers, body = build_response(urlopen_json, ITINERARY_FILE)
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    # Print the forecast as a table in the terminal (this calls the real API).
    status, _, body = build_response()
    if status != 200:
        sys.exit(json.loads(body)["error"])
    for row in json.loads(body):
        if row["status"] == "ok":
            temps = f"{row['max_temp']:>4}°F {row['min_temp']:>4}°F  {row['weather']}"
        else:
            temps = row["status"].replace("_", " ")
        print(f"{row['date']}  {row['city']:<24} {temps}")
