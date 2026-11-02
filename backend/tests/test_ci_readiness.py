"""Exercise the real workflow shell with an evaluator stub, never a model call."""

import os
from pathlib import Path
import subprocess
import shutil

import pytest
import yaml


if os.name == "nt":
    git = shutil.which("git")
    candidate = Path(git).parents[1] / "bin/bash.exe" if git else None
    BASH = str(candidate) if candidate and candidate.is_file() else None
else:
    BASH = shutil.which("bash")


@pytest.mark.skipif(not BASH, reason="Readiness shell test requires Bash (Git Bash on Windows)")
@pytest.mark.parametrize("status, expected", [(0, 0), (2, 0), (1, 1), (7, 7)])
def test_readiness_exit_policy(tmp_path, status, expected):
    workflow = yaml.safe_load(
        (Path(__file__).parents[2] / ".github/workflows/checks.yml").read_text()
    )
    script = workflow["jobs"]["evaluation-readiness"]["steps"][-1]["run"]
    summary = tmp_path / "summary.md"
    # Shell function replaces only the evaluator invocation inside the real step.
    result = subprocess.run(
        [
            BASH,
            "--noprofile",
            "--norc",
            "-e",
            "-o",
            "pipefail",
            "-c",
            'python() { return "$FIXTURE_EXIT"; }\n' + script,
        ],
        env={**os.environ, "FIXTURE_EXIT": str(status), "GITHUB_STEP_SUMMARY": summary.as_posix()},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == expected, result.stderr
    if status == 2:
        assert "NO_VERIFIED_ROWS" in summary.read_text()
        assert "No scores" in summary.read_text()
    else:
        assert not summary.exists()


@pytest.mark.skipif(not BASH, reason="Required-check shell test requires Bash")
@pytest.mark.parametrize("result", ["success", "failure", "cancelled", "skipped"])
def test_stable_required_check_gates_on_matrix(result):
    workflow = yaml.safe_load(
        (Path(__file__).parents[2] / ".github/workflows/checks.yml").read_text()
    )
    job = workflow["jobs"]["tests"]
    assert "strategy" not in job and job["needs"] == "backend-tests"
    assert job["if"] == "${{ always() }}"
    script = job["steps"][0]["run"].replace("${{ needs.backend-tests.result }}", result)
    completed = subprocess.run([BASH, "-e", "-c", script], capture_output=True, timeout=10)
    assert (completed.returncode == 0) == (result == "success")
