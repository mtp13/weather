"""Guard .vercelignore: tooling stays out of the deploy, the runtime files stay in."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IGNORED = {
    line.strip()
    for line in (REPO_ROOT / ".vercelignore").read_text().splitlines()
    if line.strip() and not line.startswith("#")
}


def test_tooling_is_not_deployed():
    for entry in (
        "tests/",
        "e2e/",
        ".github/",
        "node_modules/",
        "AGENTS.md",
        "package.json",
        "package-lock.json",
        "playwright.config.*",
    ):
        assert entry in IGNORED


def test_runtime_files_are_deployed():
    runtime = {
        "api/",
        "api",
        "itinerary.json",
        "index.html",
        "app.js",
        "style.css",
        "cruise.png",
        "vercel.json",
        "pyproject.toml",
        "uv.lock",
        ".python-version",
        "README.md",  # pyproject.toml's readme
    }
    assert not runtime & IGNORED


def test_runtime_files_exist():
    for name in ("api/weather.py", "itinerary.json", "pyproject.toml", "uv.lock"):
        assert (REPO_ROOT / name).exists()
    assert (REPO_ROOT / ".python-version").exists()


def test_vercel_json_does_not_override_python_detection():
    import json

    config = json.loads((REPO_ROOT / "vercel.json").read_text())
    assert "builds" not in config
    assert "routes" not in config
