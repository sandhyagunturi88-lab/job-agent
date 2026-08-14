"""Graph nodes.

retrieve → llm_rerank → [interrupt: pick_jobs] → (learn_preferences on dismissals)
        → tailor_cv → validate_cv (loop, max 2 retries) → [interrupt: approve_cv]
        → build_application_pack → END

LLM calls happen ONLY in llm_rerank and tailor_cv (phase 3 — currently
deterministic stubs behind app.graph.stubs). Both interrupts persist through the
checkpointer, so a run survives app closes, deploys and restarts.
"""

from jobpilot_schemas import ApplicationPack, DismissedJob, PreferenceProfile
from langgraph.types import interrupt

from app import llm
from app.core.config import get_settings
from app.graph import stubs
from app.graph.state import AgentState
from app.graph.validator import validate_tailored_cv

MAX_TAILOR_RETRIES = 2


def retrieve(state: AgentState) -> dict:
    """Hybrid search (pgvector cosine + Postgres FTS) over chunked JDs, top 50."""
    profile = state.get("preference_profile") or PreferenceProfile()
    inventory = state.get("cv_inventory") or []
    if get_settings().database_url:
        from app.retrieval import hybrid_search

        jobs = hybrid_search(profile=profile, cv_inventory=inventory, top_k=50)
    else:
        jobs = stubs.hybrid_search(profile=profile, cv_inventory=inventory, top_k=50)
    return {"candidate_jobs": jobs, "phase": "retrieve"}


def llm_rerank(state: AgentState) -> dict:
    """Single batched Claude call scoring each job 0-100 (LLM call site #1)."""
    matches = llm.rerank(
        jobs=state.get("candidate_jobs") or [],
        profile=state.get("preference_profile") or PreferenceProfile(),
        cv_inventory=state.get("cv_inventory") or [],
        user_id=state.get("user_id") or "",
        run_date=state.get("run_date") or "",
    )
    return {"matches": matches, "phase": "llm_rerank"}


def pick_jobs(state: AgentState) -> dict:
    """Interrupt 1 — the user picks jobs; dismissals carry a reason."""
    decision = interrupt(
        {
            "type": "pick_jobs",
            "matches": [m.model_dump(mode="json") for m in state.get("matches") or []],
        }
    )
    dismissals = [DismissedJob.model_validate(d) for d in decision.get("dismissals", [])]
    return {
        "selected_job_ids": list(decision.get("selected_job_ids", [])),
        "dismissals": dismissals,
        "phase": "pick_jobs",
    }


def learn_preferences(state: AgentState) -> dict:
    """Fold dismissal reasons into the preference profile used by future runs.

    Phase 2 persists the updated profile to Supabase; the graph-local update
    keeps the shape final now.
    """
    profile = (state.get("preference_profile") or PreferenceProfile()).model_copy(deep=True)
    for dismissal in state.get("dismissals") or []:
        note = f"Dismissed {dismissal.job_id}: {dismissal.reason}"
        if note not in profile.notes:
            profile.notes.append(note)
        reason = dismissal.reason.lower()
        for keyword in ("php", "wordpress", "on-site", "junior"):
            if keyword in reason and keyword not in profile.avoid_keywords:
                profile.avoid_keywords.append(keyword)
    return {"preference_profile": profile, "phase": "learn_preferences"}


def tailor_cv(state: AgentState) -> dict:
    """Tailor the CV per selected job from the master inventory only (LLM call site #2)."""
    jobs = {j.id: j for j in state.get("candidate_jobs") or []}
    inventory = state.get("cv_inventory") or []
    violations = state.get("violations") or []
    tailored = [
        llm.tailor(
            job=jobs[job_id],
            cv_inventory=inventory,
            edit_requests=state.get("edit_requests") or "",
            violations=[v for v in violations if v.job_id == job_id],
            user_id=state.get("user_id") or "",
            run_date=state.get("run_date") or "",
        )
        for job_id in state.get("selected_job_ids") or []
        if job_id in jobs
    ]
    return {"tailored_cvs": tailored, "phase": "tailor_cv"}


def validate_cv(state: AgentState) -> dict:
    """Deterministic evidence check; violations loop back to tailor_cv."""
    inventory = state.get("cv_inventory") or []
    violations = [
        v
        for cv in state.get("tailored_cvs") or []
        for v in validate_tailored_cv(cv, inventory)
    ]
    retries = state.get("tailor_retries") or 0
    return {
        "violations": violations,
        "tailor_retries": retries + 1 if violations else retries,
        "phase": "validate_cv",
    }


def flag_manual_edit(state: AgentState) -> dict:
    """Retries exhausted: strip unevidenced changes and flag the CV for manual edit."""
    bad_by_job: dict[str, set[int]] = {}
    for v in state.get("violations") or []:
        bad_by_job.setdefault(v.job_id, set()).add(v.change_index)
    flagged = []
    for cv in state.get("tailored_cvs") or []:
        bad = bad_by_job.get(cv.job_id, set())
        if bad:
            cv = cv.model_copy(deep=True)
            cv.changes = [c for i, c in enumerate(cv.changes) if i not in bad]
            cv.full_text = "\n".join(c.after for c in cv.changes)
            cv.needs_manual_edit = True
        flagged.append(cv)
    return {"tailored_cvs": flagged, "violations": [], "phase": "flag_manual_edit"}


def approve_cv(state: AgentState) -> dict:
    """Interrupt 2 — the user reviews the inline diff (each change carries its
    evidence ids for the tap-to-see evidence note) and approves or asks for edits."""
    decision = interrupt(
        {
            "type": "approve_cv",
            "tailored_cvs": [cv.model_dump(mode="json") for cv in state.get("tailored_cvs") or []],
        }
    )
    return {
        "cv_approved": bool(decision.get("approved")),
        "edit_requests": decision.get("edit_requests") or "",
        # a fresh tailor pass gets a fresh retry budget
        "tailor_retries": 0 if not decision.get("approved") else state.get("tailor_retries") or 0,
        "phase": "approve_cv",
    }


def build_application_pack(state: AgentState) -> dict:
    """Assemble the Application Pack: tailored CV + copy-ready answers + deep link.

    Consumed by the Chrome extension (desktop autofill) and the mobile copy-pack.
    The user always presses submit on the employer's site."""
    jobs = {j.id: j for j in state.get("candidate_jobs") or []}
    profile = state.get("preference_profile") or PreferenceProfile()
    packs = [
        ApplicationPack(
            job_id=cv.job_id,
            tailored_cv=cv,
            answers=stubs.copy_answers(jobs[cv.job_id], profile),
            apply_url=jobs[cv.job_id].url,
        )
        for cv in state.get("tailored_cvs") or []
        if cv.job_id in jobs
    ]
    return {"application_packs": packs, "phase": "done"}
