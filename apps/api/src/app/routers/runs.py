"""Graph run lifecycle.

One graph run per user per day (or on demand): thread_id = "{user_id}:{run_date}",
so re-triggering a day's run resumes/returns the existing thread instead of
duplicating matches or double-charging quota.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from jobpilot_schemas import ApplicationPack, PreferenceProfile
from langgraph.types import Command
from pydantic import BaseModel

from app.billing import plan_limits, week_key
from app.core.auth import CurrentUser, get_current_user
from app.graph import stubs


def _week_for_thread(thread_id: str) -> str:
    return week_key(date.fromisoformat(thread_id.split(":", 1)[1]))

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


async def _sync_after_invoke(request: Request, user: CurrentUser, thread_id: str) -> None:
    """Persist run outcomes outside the checkpointer: finished Application
    Packs feed the tracker, the learn_preferences-updated profile feeds
    tomorrow's retrieval, and weekly quota usage is recorded (keyed by
    thread, so re-invoking a day's run never double-charges)."""
    store = request.app.state.profile_store
    snap = await request.app.state.graph.aget_state(
        {"configurable": {"thread_id": thread_id}}
    )
    values = snap.values or {}
    for pack in values.get("application_packs") or []:
        if isinstance(pack, dict):
            pack = ApplicationPack.model_validate(pack)
        await run_in_threadpool(store.record_pack, user.id, pack)
    profile = values.get("preference_profile")
    if profile is not None:
        if isinstance(profile, dict):
            profile = PreferenceProfile.model_validate(profile)
        await run_in_threadpool(store.save_profile, user.id, profile)

    week = _week_for_thread(thread_id)
    interrupts = [i.value for task in snap.tasks for i in task.interrupts]
    pick = next((i for i in interrupts if i.get("type") == "pick_jobs"), None)
    if pick is not None:
        await run_in_threadpool(
            store.record_quota, user.id, thread_id, week, len(pick["matches"]), 0
        )
    cvs = values.get("tailored_cvs") or []
    if cvs:
        await run_in_threadpool(store.record_quota, user.id, thread_id, week, 0, len(cvs))


@router.get("/today")
async def get_today_run(
    request: Request, user: CurrentUser = Depends(get_current_user)
) -> dict:
    """Today's run if it exists (phase is null and next_nodes empty otherwise).

    Lets the PWA reattach to an in-flight run on load without side effects."""
    thread_id = thread_id_for(user.id, date.today().isoformat())
    return await snapshot_payload(request.app.state.graph, thread_id)


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

    # Onboarded users run with their real profile + parsed CV inventory;
    # otherwise the deterministic demo context keeps the app explorable.
    store = request.app.state.profile_store
    profile = await run_in_threadpool(store.get_profile, user.id)
    inventory = await run_in_threadpool(store.get_inventory, user.id)
    if profile is None or not inventory:
        stub_profile, stub_inventory = stubs.load_user_context(user.id)
        profile = profile or stub_profile
        inventory = inventory or stub_inventory

    # Free-plan weekly match quota (pro: unlimited). Stated, never silent.
    match_limit = None
    limits = plan_limits(await run_in_threadpool(store.get_plan, user.id))
    if limits is not None:
        week = week_key(date.fromisoformat(run_date))
        used = await run_in_threadpool(store.week_quota_usage, user.id, week)
        match_limit = max(0, limits["matches"] - used["matches"])
        if match_limit == 0:
            raise HTTPException(
                status_code=402,
                detail=(
                    f"You've seen your {limits['matches']} free matches this week. "
                    "Upgrade to Pro for unlimited matches, or new quota arrives Monday."
                ),
            )

    await graph.ainvoke(
        {
            "user_id": user.id,
            "run_date": run_date,
            "preference_profile": profile,
            "cv_inventory": inventory,
            "match_limit": match_limit,
        },
        config,
    )
    await _sync_after_invoke(request, user, thread_id)
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
    interrupts = [i.value for task in snap.tasks for i in task.interrupts]
    if not interrupts:
        raise HTTPException(status_code=409, detail="Run is not waiting for input")

    # Free-plan CV quota: picking N jobs means tailoring N CVs.
    if interrupts[0].get("type") == "pick_jobs":
        selected = len(body.value.get("selected_job_ids") or [])
        store = request.app.state.profile_store
        limits = plan_limits(await run_in_threadpool(store.get_plan, user.id))
        if limits is not None and selected > 0:
            used = await run_in_threadpool(
                store.week_quota_usage, user.id, _week_for_thread(thread_id)
            )
            remaining = max(0, limits["cvs"] - used["cvs"])
            if selected > remaining:
                raise HTTPException(
                    status_code=402,
                    detail=(
                        f"The free plan includes {limits['cvs']} tailored CV per week "
                        f"({remaining} left) — pick fewer jobs, or upgrade to Pro for "
                        "unlimited tailoring."
                    ),
                )

    await graph.ainvoke(Command(resume=body.value), config)
    await _sync_after_invoke(request, user, thread_id)
    return await snapshot_payload(graph, thread_id)
