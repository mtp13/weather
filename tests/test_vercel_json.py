"""Guard vercel.json: only the default branch deploys (** covers slash names)."""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_only_master_deploys():
    config = json.loads((REPO_ROOT / "vercel.json").read_text())
    assert config["git"]["deploymentEnabled"] == {"master": True, "**": False}
