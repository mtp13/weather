"""Shared pytest fixtures. Tests never call Open-Meteo or read the real itinerary.json.

tests/fixtures/open_meteo_*.json are real Open-Meteo daily responses, recorded on
2026-10-19 at 03:36 UTC (generationtime_ms removed). At that instant it was still
2026-10-18 in Denver but already 2026-10-19 in Barcelona.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
ITINERARY = FIXTURES / "itinerary.json"
RECORDED_AT = datetime(2026, 10, 19, 3, 36, 40, tzinfo=UTC)


def load_fixture(name):
    """Read a JSON file from tests/fixtures/"""
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def multi_response():
    """The recorded two-city response (a list): Red Rocks Park, then Barcelona"""
    return load_fixture("open_meteo_multi.json")


@pytest.fixture
def single_response():
    """The recorded one-city response (an object, not a list): Red Rocks Park"""
    return load_fixture("open_meteo_single.json")
