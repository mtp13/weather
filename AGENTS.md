# AGENTS.md - Weather Project

## Project Overview

This is a Python project for fetching weather data from the Open-Meteo API. It uses `openmeteo_requests`, `pandas`, `requests_cache`, and `retry_requests`.

- **Python Version**: 3.14+
- **Dependencies**: See `pyproject.toml`

---

## Commands

### Development Environment

```bash
# Create virtual environment and install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Add a dependency
uv add openmeteo-requests pandas requests-cache retry-requests

# Add a development dependency
uv add --dev pytest ruff mypy

# Update dependencies from pyproject.toml
uv sync
```

### Running the Application

```bash
# Run with uv (uses virtual environment)
uv run python weather.py
uv run python main.py

# Or after activating the environment
source .venv/bin/activate
python weather.py
```

### Testing

```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_weather.py

# Run a single test
pytest tests/test_weather.py::test_function_name

# Run tests with verbose output
pytest -v

# Run tests matching a pattern
pytest -k "test_name_pattern"
```

### Linting & Type Checking

```bash
# Run ruff linter
ruff check .

# Run ruff with auto-fix
ruff check --fix .

# Run mypy type checker
mypy .

# Run all checks
ruff check . && mypy .
```

### Code Formatting

```bash
# Format code with ruff
ruff format .
```

---

## Code Style Guidelines

### General Principles

- Keep functions small and focused (ideally under 50 lines)
- Use descriptive names for variables, functions, and classes
- Write docstrings for all public functions and classes
- Handle errors explicitly with specific exception types

### Imports

- Use absolute imports (not relative)
- Group imports in this order: standard library, third-party, local
- Sort imports alphabetically within each group
- Use `import x` for modules, `from x import y` for specific names

```python
# Correct
import os
import sys
from collections.abc import Iterator

import pandas as pd
import requests_cache
from retry_requests import retry

from weather import constants
from weather.utils import format_date
```

### Formatting

- Maximum line length: 100 characters
- Use 4 spaces for indentation (no tabs)
- Use snake_case for functions, variables, and file names
- Use PascalCase for classes
- Use SCREAMING_SNAKE_CASE for constants
- Use type hints for all function parameters and return values
- Prefer f-strings over .format() and % formatting

```python
# Function with type hints
def fetch_weather_data(latitude: float, longitude: float) -> dict[str, Any]:
    """Fetch weather data for the given coordinates.
    
    Args:
        latitude: Latitude of the location.
        longitude: Longitude of the location.
    
    Returns:
        Dictionary containing weather data.
    
    Raises:
        ValueError: If coordinates are invalid.
        APIError: If the API request fails.
    """
    pass
```

### Naming Conventions

- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/variables**: `snake_case`
- **Constants**: `SCREAMING_SNAKE_CASE`
- **Private members**: Prefix with underscore `_private_method()`
- **Type variables**: `PascalCase` (e.g., `T`, `TResult`)

### Type Annotations

- Always use type hints for function signatures
- Use `Any` sparingly - prefer specific types when possible
- Use `Optional[X]` instead of `X | None`
- Use `dict[str, Any]` for heterogeneous dictionaries
- Use `list[int]`, `set[str]`, `tuple[str, int]` instead of `List`, `Set`, `Tuple`

### Error Handling

- Use specific exception types (create custom exceptions when needed)
- Never catch bare `Exception` or `BaseException` unless re-raising
- Include meaningful error messages in exceptions
- Use context managers (`with`) for resource management

```python
# Good error handling
class APIError(Exception):
    """Raised when the API request fails."""
    pass


def fetch_weather(url: str, params: dict) -> dict:
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        raise APIError(f"Failed to fetch weather: {e}") from e
```

### Testing

- Place tests in a `tests/` directory
- Name test files `test_<module>.py`
- Name test functions `test_<description>()`
- Use descriptive test names that explain the expected behavior
- Use pytest fixtures for shared test setup
- Aim for high test coverage on business logic

```python
# Example test
import pytest
from weather import fetch


def test_fetch_weather_returns_valid_data():
    """Test that fetch_weather returns properly formatted data."""
    result = fetch.fetch_weather(latitude=52.52, longitude=13.41)
    
    assert isinstance(result, dict)
    assert "temperature" in result
    assert result["temperature"] is not None
```

### Git Practices

- Write meaningful commit messages
- Keep commits atomic and focused
- Use feature branches for new features
- Run linting and type checking before committing

---

## Project Structure

```
weather/
├── .venv/           # Virtual environment (not committed)
├── .cache/          # HTTP cache (not committed)
├── weather.py       # Main weather fetching code
├── main.py          # Entry point
├── pyproject.toml   # Project configuration
├── README.md        # Project documentation
└── tests/           # Test directory (create as needed)
```

---

## Adding Dependencies

Use `uv add` to add dependencies:

```bash
# Add runtime dependency
uv add openmeteo-requests pandas requests-cache retry-requests

# Add development dependency
uv add --dev pytest ruff mypy
```

This automatically updates `pyproject.toml`. Alternatively, manually edit the file:

```toml
[project]
dependencies = [
    "openmeteo-requests",
    "pandas",
    "requests-cache",
    "retry-requests",
]
```

For development dependencies, add a `[project.optional-dependencies]` section or use a separate `requirements-dev.txt`.
