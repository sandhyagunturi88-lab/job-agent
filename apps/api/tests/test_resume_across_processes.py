"""Checkpointer resume tests with REAL process death.

Every step runs in a separate Python process against a shared checkpointer
(SQLite file by default; the same tests run against real Postgres when
TEST_DATABASE_URL is set — that's the CI/staging configuration). Between steps
the process is gone — state lives only in the checkpointer, exactly like a
deploy or an app close between the user's morning picks and evening approval.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

RUNNER = Path(__file__).parent / "process_runner.py"
SRC = Path(__file__).parent.parent / "src"

DSNS = ["sqlite"]
if os.environ.get("TEST_DATABASE_URL"):
    DSNS.append("postgres")


def _dsn(kind: str, tmp_path: Path) -> str:
    if kind == "postgres":
        return os.environ["TEST_DATABASE_URL"]
    return str(tmp_path / "checkpoints.db")


def _run(command: list[str], dsn: str, thread: str, env_extra: dict | None = None) -> dict:
    env = {
        **os.environ,
        "PYTHONPATH": str(SRC),
        "JOBPILOT_TEST_DB": dsn,
        "JOBPILOT_TEST_THREAD": thread,
        **(env_extra or {}),
    }
    result = subprocess.run(
        [sys.executable, str(RUNNER), *command],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("kind", DSNS)
def test_run_survives_process_exit_between_interrupts(kind, tmp_path):
    """Process 1 starts the run and DIES. Process 2 picks jobs and DIES.
    Process 3 approves. Three different processes, one continuous run."""
    dsn = _dsn(kind, tmp_path)
    thread = f"proc-user:exit-{kind}-{tmp_path.name}"

    first = _run(["start"], dsn, thread)
    assert first["interrupt_type"] == "pick_jobs"
    job_id = first["match_ids"][0]

    second = _run(["pick", job_id], dsn, thread)
    assert second["interrupt_type"] == "approve_cv"

    third = _run(["approve"], dsn, thread)
    assert third["phase"] == "done"
    assert third["packs"] == 1

    # And a fourth process can still read the finished state.
    assert _run(["status"], dsn, thread)["phase"] == "done"


@pytest.mark.parametrize("kind", DSNS)
def test_run_killed_mid_node_resumes_from_last_checkpoint(kind, tmp_path):
    """Kill -9 the process WHILE a node is executing (mid-rerank). The
    checkpoint after retrieve survives; a fresh process re-runs rerank and
    reaches interrupt 1 as if nothing happened."""
    dsn = _dsn(kind, tmp_path)
    thread = f"proc-user:kill-{kind}-{tmp_path.name}"
    marker = tmp_path / "retrieve-done.marker"

    env = {
        **os.environ,
        "PYTHONPATH": str(SRC),
        "JOBPILOT_TEST_DB": dsn,
        "JOBPILOT_TEST_THREAD": thread,
        "JOBPILOT_SLOW_RERANK": "30",
        "JOBPILOT_MARKER_FILE": str(marker),
    }
    proc = subprocess.Popen(
        [sys.executable, str(RUNNER), "start"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 60
        while not marker.exists():  # retrieve checkpointed, rerank sleeping
            assert time.monotonic() < deadline, "retrieve never completed"
            assert proc.poll() is None, proc.stderr.read().decode()
            time.sleep(0.05)
        time.sleep(0.3)  # let the retrieve checkpoint flush, then kill mid-rerank
    finally:
        proc.kill()
    proc.wait(timeout=30)

    # Fresh process, no slow-rerank env: continue from the last checkpoint.
    resumed = _run(["resume-none"], dsn, thread)
    assert resumed["interrupt_type"] == "pick_jobs"
    assert resumed["match_ids"]

    # The run then completes normally across further fresh processes.
    picked = _run(["pick", resumed["match_ids"][0]], dsn, thread)
    assert picked["interrupt_type"] == "approve_cv"
    assert _run(["approve"], dsn, thread)["phase"] == "done"
