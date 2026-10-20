"""Guard vercel.json: only the default branch deploys (** covers slash names)."""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_only_master_deploys():
    config = json.loads((REPO_ROOT / "vercel.json").read_text())
    assert config["git"]["deploymentEnabled"] == {"master": True, "**": False}


def test_deploys_the_branch_ci_runs_on():
    config = json.loads((REPO_ROOT / "vercel.json").read_text())
    deployed = [
        branch
        for branch, enabled in config["git"]["deploymentEnabled"].items()
        if enabled
    ]
    ci = (REPO_ROOT / ".github/workflows/ci.yml").read_text()
    ci_branches = set()
    for group in re.findall(r"branches:\s*\[([^\]]*)\]", ci):
        ci_branches.update(part.strip() for part in group.split(",") if part.strip())
    for branch in re.findall(r"^\s*-\s+(\S+)\s*$", ci, re.MULTILINE):
        ci_branches.add(branch)
    for branch in deployed:
        assert branch in ci_branches, (
            f"CI does not run on {branch}, so it would never be deployed"
        )
