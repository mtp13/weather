"""Tests for the pure helpers in api/weather.py. They never touch the network."""

import datetime

from api import weather


def test_known_weather_code_has_a_description():
    assert weather.get_weather_description(0) == "Clear sky"
    assert weather.get_weather_description(95) == "Thunderstorm"


def test_unknown_weather_code_is_unknown():
    assert weather.get_weather_description(42) == "Unknown"


def test_worst_code_prefers_thunder_over_rain():
    assert weather.get_worst_weather_code([0, 61, 95, 63]) == 95


def test_worst_code_falls_back_to_the_first_code():
    assert weather.get_worst_weather_code([3, 0, 45]) == 3


def test_worst_code_of_no_codes_is_clear_sky():
    assert weather.get_worst_weather_code([]) == 0


def test_load_itinerary_parses_iso_dates():
    cities = weather.load_itinerary()
    assert cities
    for city in cities:
        assert {"name", "country", "latitude", "longitude", "dates"} <= city.keys()
        assert all(isinstance(d, datetime.date) for d in city["dates"])
