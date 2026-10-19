"""Tests for api/weather.py. They never touch the network: `fetch` is injected."""

import io
import json
from datetime import UTC, date, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

import pytest
from conftest import ITINERARY, RECORDED_AT

from api import weather


def by_city_and_date(results):
    return {(r["city"], r["date"]): r for r in results}


# --- load_itinerary ---------------------------------------------------------


def test_load_itinerary_parses_iso_dates():
    cities = weather.load_itinerary(ITINERARY)
    assert [c["name"] for c in cities] == ["Red Rocks Park", "Barcelona"]
    assert cities[0]["dates"][0] == date(2026, 10, 17)


def test_default_itinerary_path_is_next_to_the_api_folder():
    assert weather.ITINERARY_FILE.name == "itinerary.json"
    assert weather.ITINERARY_FILE.parent == weather.Path(weather.__file__).parent.parent


# --- get_weather_description and round_temp ---------------------------------


@pytest.mark.parametrize(
    ("code", "description"),
    [(0, "Clear sky"), (45, "Fog"), (75, "Heavy snow"), (95, "Thunderstorm")],
)
def test_known_weather_codes(code, description):
    assert weather.get_weather_description(code) == description


def test_unknown_weather_code_is_unknown():
    assert weather.get_weather_description(42) == "Unknown"


def test_missing_weather_code_stays_none():
    assert weather.get_weather_description(None) is None


@pytest.mark.parametrize(
    ("value", "rounded"), [(52.5, 53), (43.6, 44), (72.4, 72), (-0.5, 0), (-3.6, -4)]
)
def test_round_temp_rounds_half_up(value, rounded):
    assert weather.round_temp(value) == rounded


# --- forecast_url -----------------------------------------------------------


def test_one_url_covers_every_city_with_local_days():
    url = weather.forecast_url(weather.load_itinerary(ITINERARY))
    parts = urlsplit(url)
    query = {k: v[0] for k, v in parse_qs(parts.query).items()}
    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == weather.FORECAST_URL
    assert query == {
        "latitude": "39.67,41.39",
        "longitude": "-105.2,2.17",
        "daily": "temperature_2m_max,temperature_2m_min,weather_code",
        "timezone": "auto",
        "temperature_unit": "fahrenheit",
        "forecast_days": "16",
    }


# --- fetch_forecasts --------------------------------------------------------


def test_fetch_makes_one_request_for_all_cities(multi_response):
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return multi_response

    cities = weather.load_itinerary(ITINERARY)
    assert weather.fetch_forecasts(cities, fetch=fake_fetch) == multi_response
    assert calls == [weather.forecast_url(cities)]


def test_fetch_wraps_a_single_city_object_in_a_list(single_response):
    cities = weather.load_itinerary(ITINERARY)[:1]
    forecasts = weather.fetch_forecasts(cities, fetch=lambda url: single_response)
    assert forecasts == [single_response]


def test_fetch_retries_a_network_error_once(multi_response):
    attempts = []

    def flaky_fetch(url):
        attempts.append(url)
        if len(attempts) == 1:
            raise URLError("connection reset")
        return multi_response

    cities = weather.load_itinerary(ITINERARY)
    assert weather.fetch_forecasts(cities, fetch=flaky_fetch) == multi_response
    assert len(attempts) == 2


def test_fetch_gives_up_after_two_network_errors():
    attempts = []

    def down(url):
        attempts.append(url)
        raise TimeoutError("timed out")

    with pytest.raises(weather.ForecastError, match="Could not reach"):
        weather.fetch_forecasts(weather.load_itinerary(ITINERARY), fetch=down)
    assert len(attempts) == 2


def test_fetch_does_not_retry_a_client_error():
    attempts = []

    def bad_request(url):
        attempts.append(url)
        raise HTTPError(url, 400, "Bad Request", None, io.BytesIO())

    with pytest.raises(weather.ForecastError, match="HTTP 400"):
        weather.fetch_forecasts(weather.load_itinerary(ITINERARY), fetch=bad_request)
    assert len(attempts) == 1


def test_fetch_rejects_an_api_error_object():
    error = {"error": True, "reason": "Latitude must be in range of -90 to 90°."}
    with pytest.raises(weather.ForecastError, match="Latitude"):
        weather.fetch_forecasts(
            weather.load_itinerary(ITINERARY)[:1], fetch=lambda url: error
        )


def test_fetch_rejects_a_response_with_the_wrong_number_of_cities(single_response):
    with pytest.raises(weather.ForecastError, match="unexpected"):
        weather.fetch_forecasts(
            weather.load_itinerary(ITINERARY), fetch=lambda url: [single_response]
        )


# --- build_results ----------------------------------------------------------


@pytest.fixture
def results(multi_response):
    itinerary = weather.load_itinerary(ITINERARY)
    return weather.build_results(itinerary, multi_response, RECORDED_AT)


def test_results_are_sorted_by_date_with_a_status_each(results):
    assert [r["date"] for r in results] == sorted(r["date"] for r in results)
    assert len(results) == 8
    assert {r["status"] for r in results} == {"ok", "past", "out_of_range"}
    for r in results:
        assert set(r) == {
            "date",
            "city",
            "country",
            "max_temp",
            "min_temp",
            "weather",
            "status",
        }


def test_a_date_in_range_has_whole_degree_temperatures(results):
    barcelona = by_city_and_date(results)[("Barcelona", "2026-10-20")]
    assert barcelona == {
        "date": "2026-10-20",
        "city": "Barcelona",
        "country": "Spain",
        "max_temp": 71,
        "min_temp": 63,
        "weather": "Thunderstorm",
        "status": "ok",
    }


def test_the_local_date_is_used_not_the_utc_date(results):
    """At 03:36 UTC on Oct 19 it is still Oct 18 in Denver (UTC-6), so Oct 18
    is today there and uses Denver's local-day high and low (fix #1). In
    Barcelona (UTC+2) it is already Oct 19, so Oct 18 has passed."""
    rows = by_city_and_date(results)
    assert RECORDED_AT.date() == date(2026, 10, 19)

    red_rocks_today = rows[("Red Rocks Park", "2026-10-18")]
    assert red_rocks_today["status"] == "ok"
    assert (red_rocks_today["max_temp"], red_rocks_today["min_temp"]) == (73, 53)
    assert red_rocks_today["weather"] == "Overcast"

    assert rows[("Barcelona", "2026-10-18")]["status"] == "past"


def test_a_past_date_has_no_forecast(results):
    past = by_city_and_date(results)[("Red Rocks Park", "2026-10-17")]
    assert past["status"] == "past"
    assert past["max_temp"] is past["min_temp"] is past["weather"] is None


def test_a_date_beyond_the_window_is_out_of_range(results):
    rows = by_city_and_date(results)
    assert rows[("Red Rocks Park", "2026-11-03")]["status"] == "out_of_range"
    # Barcelona's 16th day is in the response but null, so it isn't available yet.
    assert rows[("Barcelona", "2026-11-03")]["status"] == "out_of_range"
    assert rows[("Barcelona", "2026-11-03")]["max_temp"] is None
    assert rows[("Barcelona", "2026-11-02")]["status"] == "ok"
    assert rows[("Barcelona", "2026-11-02")]["weather"] == "Fog"


def test_every_date_passed(multi_response):
    itinerary = weather.load_itinerary(ITINERARY)
    later = datetime(2026, 12, 1, tzinfo=UTC)
    results = weather.build_results(itinerary, multi_response, later)
    assert {r["status"] for r in results} == {"past"}


def test_an_empty_itinerary_has_no_results():
    assert weather.build_results([], [], RECORDED_AT) == []


# --- build_response and the handler -----------------------------------------


def test_response_is_cached_json(multi_response):
    status, headers, body = weather.build_response(
        fetch=lambda url: multi_response, itinerary_path=ITINERARY, now=RECORDED_AT
    )
    assert status == 200
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert headers["Cache-Control"] == (
        "public, s-maxage=1800, stale-while-revalidate=3600"
    )
    assert len(json.loads(body)) == 8


def test_upstream_failure_is_502_json_without_a_traceback(capsys):
    def down(url):
        raise URLError("no route to host")

    status, headers, body = weather.build_response(fetch=down, itinerary_path=ITINERARY)
    assert status == 502
    assert headers["Cache-Control"] == "no-store"
    assert json.loads(body) == {"error": "The weather service is unavailable."}
    assert b"Traceback" not in body
    assert "no route to host" in capsys.readouterr().err


def test_unexpected_failure_is_500_json_and_logged(tmp_path, capsys):
    broken = tmp_path / "itinerary.json"
    broken.write_text("{not json")
    status, _, body = weather.build_response(
        fetch=lambda url: pytest.fail("should not fetch"), itinerary_path=broken
    )
    assert status == 500
    assert json.loads(body) == {"error": "Something went wrong."}
    assert "Traceback" in capsys.readouterr().err


def run_handler():
    """Run handler.do_GET without a socket and return (status line, headers, body)"""
    h = weather.handler.__new__(weather.handler)
    h.request_version = "HTTP/1.1"
    h.requestline = "GET /api/weather HTTP/1.1"
    h.command = "GET"
    h.client_address = ("127.0.0.1", 0)
    h.wfile = io.BytesIO()
    h.do_GET()
    head, _, body = h.wfile.getvalue().partition(b"\r\n\r\n")
    status_line, *header_lines = head.decode().split("\r\n")
    headers = dict(line.split(": ", 1) for line in header_lines)
    return status_line, headers, body


def test_handler_returns_200_with_the_cache_header(monkeypatch, multi_response):
    monkeypatch.setattr(weather, "ITINERARY_FILE", ITINERARY)
    monkeypatch.setattr(weather, "urlopen_json", lambda url: multi_response)
    status_line, headers, body = run_handler()
    assert status_line.split()[1] == "200"
    assert headers["Cache-Control"] == weather.CACHE_CONTROL
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert all("status" in row for row in json.loads(body))


def test_handler_returns_502_json_when_fetch_raises(monkeypatch):
    def down(url):
        raise URLError("down")

    monkeypatch.setattr(weather, "ITINERARY_FILE", ITINERARY)
    monkeypatch.setattr(weather, "urlopen_json", down)
    status_line, headers, body = run_handler()
    assert status_line.split()[1] == "502"
    assert headers["Cache-Control"] == "no-store"
    assert json.loads(body) == {"error": "The weather service is unavailable."}
