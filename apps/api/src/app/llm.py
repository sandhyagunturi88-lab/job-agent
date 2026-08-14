"""The graph's ONLY two LLM call sites: rerank and tailor (cost control).

With ANTHROPIC_API_KEY set, both call Claude via langchain-anthropic (which
wraps the official Anthropic SDK) using structured outputs — one single batched
call per node. Without a key they fall back to the deterministic stubs, so dev
and tests run free and offline. Every real call records token usage per node
per user (app.usage).

Model default is claude-opus-5 (see Settings.anthropic_model). Opus 5 notes:
thinking is on by default and max_tokens caps thinking + response text, so we
give generous headroom; sampling params (temperature/top_p/top_k) are removed
on Opus-tier models and are never sent.
"""

from functools import lru_cache

from jobpilot_schemas import (
    CVChange,
    CVInventoryItem,
    Job,
    JobMatch,
    PreferenceProfile,
    TailoredCV,
    ValidationViolation,
)
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.graph import stubs
from app.usage import UsageRow, record_usage

MAX_TOKENS = 32000
JD_EXCERPT_CHARS = 1500


# --- structured output schemas ------------------------------------------------


class RerankItem(BaseModel):
    job_id: str
    score: int = Field(ge=0, le=100)
    matched_skills: list[str] = []
    gaps: list[str] = []
    verdict: str = Field(description="One-line verdict on fit")


class RerankOutput(BaseModel):
    results: list[RerankItem]


class TailorOutput(BaseModel):
    changes: list[CVChange]


# --- client -------------------------------------------------------------------


@lru_cache
def _chat_model():
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=settings.anthropic_model,
        max_tokens=MAX_TOKENS,
        api_key=settings.anthropic_api_key,
    )


def _record(node: str, raw_message, user_id: str, run_date: str) -> None:
    usage = getattr(raw_message, "usage_metadata", None) or {}
    record_usage(
        UsageRow(
            user_id=user_id,
            run_date=run_date,
            node=node,
            model=get_settings().anthropic_model,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )
    )


# --- rerank -------------------------------------------------------------------

_RERANK_SYSTEM = """You score UK job postings for one specific job seeker.

For EVERY job listed, return: its job_id verbatim; a fit score 0-100 (100 = the
candidate should apply today); matched_skills — only skills evidenced in the
candidate's CV inventory that the job actually asks for; gaps — requirements
the job asks for that the CV does not evidence; and a one-line verdict a busy
person can act on. Respect the candidate's stated preferences (salary floor,
locations, contract types, avoid list) when scoring. Score every job; never
skip or invent job_ids."""


def rerank(
    jobs: list[Job],
    profile: PreferenceProfile,
    cv_inventory: list[CVInventoryItem],
    user_id: str = "",
    run_date: str = "",
) -> list[JobMatch]:
    llm = _chat_model()
    if llm is None:
        return stubs.rerank(jobs, profile, cv_inventory)

    jobs_block = "\n\n".join(
        f"job_id: {j.id}\n{j.title} at {j.company} — {j.location}"
        f"\nsalary: {j.salary_min}-{j.salary_max} | contract: {j.contract_type}"
        f" | inside IR35: {j.ir35_flag}\nJD: {j.jd_text[:JD_EXCERPT_CHARS]}"
        for j in jobs
    )
    inventory_block = "\n".join(f"[{i.id}] ({i.kind}) {i.text}" for i in cv_inventory)
    prompt = (
        f"CANDIDATE CV INVENTORY:\n{inventory_block}\n\n"
        f"CANDIDATE PREFERENCES:\n{profile.model_dump_json()}\n\n"
        f"JOBS TO SCORE ({len(jobs)}):\n{jobs_block}"
    )

    structured = llm.with_structured_output(RerankOutput, include_raw=True)
    result = structured.invoke([("system", _RERANK_SYSTEM), ("human", prompt)])
    _record("llm_rerank", result["raw"], user_id, run_date)

    by_id = {j.id: j for j in jobs}
    matches = [
        JobMatch(
            job=by_id[item.job_id],
            score=item.score,
            matched_skills=item.matched_skills,
            gaps=item.gaps,
            verdict=item.verdict,
        )
        for item in result["parsed"].results
        if item.job_id in by_id
    ]
    return sorted(matches, key=lambda m: m.score, reverse=True)


# --- tailor -------------------------------------------------------------------

_TAILOR_SYSTEM = """You tailor a candidate's CV for one specific job.

HARD RULE — the evidence-only guarantee: every change you propose must be
constructed ONLY from the CV inventory items provided, and must cite the ids of
the items it draws on in evidence_ids. Never introduce a skill, employer,
figure, date or claim that does not appear verbatim-or-paraphrased in a cited
inventory item. Numbers especially: a figure may appear in `after` only if the
same figure appears in a cited item. A deterministic validator rejects any
violation and your output will be discarded.

Order changes so the most job-relevant evidence leads. Keep `after` text tight
and factual. Use `before` only when rewording an existing section."""


def tailor(
    job: Job,
    cv_inventory: list[CVInventoryItem],
    edit_requests: str = "",
    violations: list[ValidationViolation] | None = None,
    user_id: str = "",
    run_date: str = "",
) -> TailoredCV:
    llm = _chat_model()
    if llm is None:
        return stubs.tailor(job, cv_inventory, edit_requests, violations)

    inventory_block = "\n".join(f"[{i.id}] ({i.kind}) {i.text}" for i in cv_inventory)
    prompt_parts = [
        f"TARGET JOB:\n{job.title} at {job.company} — {job.location}\nJD: {job.jd_text}",
        f"CV INVENTORY (the only permitted source material):\n{inventory_block}",
    ]
    if edit_requests:
        prompt_parts.append(f"USER'S EDIT REQUESTS (honour these):\n{edit_requests}")
    if violations:
        prompt_parts.append(
            "YOUR PREVIOUS ATTEMPT FAILED VALIDATION — fix these violations:\n"
            + "\n".join(f"- change #{v.change_index}: {v.problem}" for v in violations)
        )

    structured = llm.with_structured_output(TailorOutput, include_raw=True)
    result = structured.invoke([("system", _TAILOR_SYSTEM), ("human", "\n\n".join(prompt_parts))])
    _record("tailor_cv", result["raw"], user_id, run_date)

    changes = result["parsed"].changes
    return TailoredCV(
        job_id=job.id,
        changes=changes,
        full_text="\n".join(c.after for c in changes),
    )
