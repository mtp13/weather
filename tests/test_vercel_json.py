"""Guard vercel.json: only the default branch deploys (** covers slash names)."""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BRANCH = "master"


def _enabled():
    config = json.loads((REPO_ROOT / "vercel.json").read_text())
    return config["git"]["deploymentEnabled"]


def test_default_branch_deploys_and_catch_all_is_blocked():
    enabled = _enabled()
    assert enabled[DEFAULT_BRANCH] is True, (
        "the default branch must deploy, or production stops updating"
    )
    assert enabled["**"] is False, (
        "the catch-all rule must stay false, or branch previews eat the daily budget"
    )


def test_ci_runs_on_the_default_branch():
    ci = (REPO_ROOT / ".github/workflows/ci.yml").read_text()
    branches = set()
    for group in re.findall(r"branches:\s*\[([^\]]*)\]", ci):
        branches.update(part.strip() for part in group.split(",") if part.strip())
    for branch in re.findall(r"^\s*-\s+(\S+)\s*$", ci, re.MULTILINE):
        branches.add(branch)
    assert DEFAULT_BRANCH in branches, (
        "CI does not run on the default branch, so a merge records no CI run"
    )
