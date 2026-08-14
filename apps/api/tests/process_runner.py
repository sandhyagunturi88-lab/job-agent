"""Subprocess runner for the kill-the-process resume tests.

Each invocation is a FRESH Python process that opens the shared checkpointer
(SQLite file, or Postgres when JOBPILOT_TEST_DB is a postgres:// URL), builds
the graph, performs ONE step, prints a JSON result and exits. The test kills
processes between (and during) steps; the checkpointer is the only thing that
survives — exactly what production relies on across deploys and restarts.

Commands:
  start        run a new thread up to interrupt 1 (pick_jobs)
  pick <id>    resume interrupt 1 selecting one job
  approve      resume interrupt 2 approving the CV
  resume-none  invoke(None): continue a run that was killed mid-node
  status       print pending interrupt + phase without mutating anything

Env:
  JOBPILOT_TEST_DB       sqlite file path or postgres:// URL (required)
  JOBPILOT_TEST_THREAD   thread id (required)
  JOBPILOT_SLOW_RERANK   seconds to sleep inside rerank (to be killed mid-node)
  JOBPILOT_MARKER_FILE   file touched right after retrieve completes
"""

import json
import os
import sys
import time
from contextlib import contextmanager

from app.graph import stubs
from app.graph.build import build_graph
from langgraph.types import Command


@contextmanager
def open_saver(dsn: str):
    if dsn.startswith("postgres"):
        from langgraph.checkpoint.postgres import PostgresSaver

        with PostgresSaver.from_conn_string(dsn) as saver:
            saver.setup()
            yield saver
    else:
        from langgraph.checkpoint.sqlite import SqliteSaver

        with SqliteSaver.from_conn_string(dsn) as saver:
            yield saver


def install_test_hooks() -> None:
    slow = float(os.environ.get("JOBPILOT_SLOW_RERANK", "0"))
    marker = os.environ.get("JOBPILOT_MARKER_FILE", "")
    if marker:
        real_search = stubs.hybrid_search

        def marked_search(*args, **kwargs):
            jobs = real_search(*args, **kwargs)
            with open(marker, "w") as f:
                f.write("retrieve-done")
            return jobs

        stubs.hybrid_search = marked_search
    if slow:
        real_rerank = stubs.rerank

        def slow_rerank(*args, **kwargs):
            time.sleep(slow)  # the test kills us during this sleep
            return real_rerank(*args, **kwargs)

        stubs.rerank = slow_rerank


def pending_interrupt(graph, config):
    snap = graph.get_state(config)
    interrupts = [i.value for task in snap.tasks for i in task.interrupts]
    return interrupts[0] if interrupts else None


def main() -> None:
    command = sys.argv[1]
    dsn = os.environ["JOBPILOT_TEST_DB"]
    thread_id = os.environ["JOBPILOT_TEST_THREAD"]
    config = {"configurable": {"thread_id": thread_id}}
    install_test_hooks()

    with open_saver(dsn) as saver:
        graph = build_graph(checkpointer=saver)

        if command == "start":
            profile, inventory = stubs.load_user_context("proc-user")
            graph.invoke(
                {
                    "user_id": "proc-user",
                    "run_date": "2026-08-14",
                    "preference_profile": profile,
                    "cv_inventory": inventory,
                },
                config,
            )
        elif command == "pick":
            graph.invoke(Command(resume={"selected_job_ids": [sys.argv[2]]}), config)
        elif command == "approve":
            graph.invoke(Command(resume={"approved": True}), config)
        elif command == "resume-none":
            graph.invoke(None, config)
        elif command != "status":
            raise SystemExit(f"unknown command {command}")

        snap = graph.get_state(config)
        interrupt = pending_interrupt(graph, config)
        print(
            json.dumps(
                {
                    "phase": (snap.values or {}).get("phase"),
                    "interrupt_type": interrupt.get("type") if interrupt else None,
                    "match_ids": [m["job"]["id"] for m in interrupt["matches"]]
                    if interrupt and interrupt.get("type") == "pick_jobs"
                    else [],
                    "packs": len((snap.values or {}).get("application_packs") or []),
                }
            )
        )


if __name__ == "__main__":
    main()
