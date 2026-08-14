"""Graph state for one daily run of a user's job agent."""

from typing import TypedDict

from jobpilot_schemas import (
    ApplicationPack,
    CVInventoryItem,
    DismissedJob,
    Job,
    JobMatch,
    PreferenceProfile,
    TailoredCV,
    ValidationViolation,
)


class AgentState(TypedDict, total=False):
    # Identity / run key
    user_id: str
    run_date: str  # ISO date; thread_id = f"{user_id}:{run_date}" (idempotent per day)

    # Inputs loaded at run start
    preference_profile: PreferenceProfile
    cv_inventory: list[CVInventoryItem]
    # Free-plan weekly match quota remaining at run start; None/absent = unlimited
    match_limit: int | None

    # retrieve -> llm_rerank
    candidate_jobs: list[Job]
    matches: list[JobMatch]

    # interrupt 1: user picks jobs
    selected_job_ids: list[str]
    dismissals: list[DismissedJob]

    # tailor_cv <-> validate_cv loop
    tailored_cvs: list[TailoredCV]
    violations: list[ValidationViolation]
    tailor_retries: int
    edit_requests: str  # free-text edit asks from interrupt 2

    # interrupt 2: user approves CV diff
    cv_approved: bool

    # final output
    application_packs: list[ApplicationPack]

    # streamed to the client over WebSocket
    phase: str
