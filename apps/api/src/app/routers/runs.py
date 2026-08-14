"""Graph run lifecycle.

One graph run per user per day (or on demand): thread_id = "{user_id}:{run_date}",
so re-triggering a day's run resumes/returns the existing thread instead of
duplicating matches or double-charging quota.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from langgraph.types import Command
from pydantic import BaseModel

from app.core.auth import CurrentUser, get_current_user
from app.graph import stubs

router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


class StartRunRequest(BaseModel):
    run_date: str | None = None  # ISO date; defaults to today


class ResumeRequest(BaseModel):
    value: dict[str, Any]  # payload answering the pending interrupt


def thread_id_for(user_id: str, run_date: str) -> str:
    return f"{user_id}:{run_date}"


async def snapshot_payload(graph, thread_id: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    snap = await graph.aget_state(config)
    interrupts = [i.value for task in snap.tasks for i in task.interrupts]
    values = snap.values or {}
    return {
        "thread_id": thread_id,
        "phase": values.get("phase"),
        "next_nodes": list(snap.next),
        "interrupt": interrupts[0] if interrupts else None,
        "values": {
            k: v
            for k, v in values.items()
            # candidate_jobs is internal; matches carry everything the client needs
            if k not in {"candidate_jobs"}
        },
    }


def _guard_thread(thread_id: str, user: CurrentUser) -> None:
    if not thread_id.startswith(f"{user.id}:"):
        raise HTTPException(status_code=404, detail="Run not found")


@router.post("/start")
async def start_run(
    body: StartRunRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    graph = request.app.state.graph
    run_date = body.run_date or date.today().isoformat()
    thread_id = thread_id_for(user.id, run_date)
    config = {"configurable": {"thread_id": thread_id}}

    existing = await graph.aget_state(config)
    if existing.values:
        # Idempotent: the day's run already exists — return it, never duplicate.
        return await snapshot_payload(graph, thread_id)

    profile, inventory = stubs.load_user_context(user.id)
    await graph.ainvoke(
        {
            "user_id": user.id,
            "run_date": run_date,
            "preference_profile": profile,
            "cv_inventory": inventory,
        },
        config,
    )
    return await snapshot_payload(graph, thread_id)


@router.get("/{thread_id}")
async def get_run(
    thread_id: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    _guard_thread(thread_id, user)
    return await snapshot_payload(request.app.state.graph, thread_id)


@router.post("/{thread_id}/resume")
async def resume_run(
    thread_id: str,
    body: ResumeRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    _guard_thread(thread_id, user)
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}

    snap = await graph.aget_state(config)
    if not any(task.interrupts for task in snap.tasks):
        raise HTTPException(status_code=409, detail="Run is not waiting for input")

    await graph.ainvoke(Command(resume=body.value), config)
    return await snapshot_payload(graph, thread_id)
