"""Shared data models for JobPilot UK.

Single source of truth for shapes that cross service boundaries
(worker -> DB -> API -> web/extension). The TypeScript types in
packages/schemas/src/index.ts mirror these and must be kept in sync.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ContractType = Literal["permanent", "contract", "temporary", "part_time", "internship"]
JobSource = Literal["adzuna", "reed", "dwp_find_a_job", "greenhouse", "lever", "workable"]


class Job(BaseModel):
    """Normalised job posting — one schema across all ingestion sources."""

    id: str
    title: str
    company: str
    location: str
    salary_min: int | None = None
    salary_max: int | None = None
    contract_type: ContractType | None = None
    ir35_flag: bool | None = None
    source: JobSource
    url: str
    jd_text: str
    posted_at: datetime


class JobMatch(BaseModel):
    """A job scored for a specific user by llm_rerank."""

    job: Job
    score: int = Field(ge=0, le=100)
    matched_skills: list[str] = []
    gaps: list[str] = []
    verdict: str = ""  # one-line LLM verdict


class DismissedJob(BaseModel):
    job_id: str
    reason: str


class PreferenceProfile(BaseModel):
    """Learned + declared preferences used by retrieve/rerank."""

    desired_titles: list[str] = []
    locations: list[str] = []
    min_salary: int | None = None
    contract_types: list[ContractType] = []
    avoid_keywords: list[str] = []  # grown by learn_preferences from dismissal reasons
    notes: list[str] = []


class CVInventoryItem(BaseModel):
    """One evidenced fact from the user's master CV. The ONLY permitted
    source material for tailored CVs (evidence-only guarantee)."""

    id: str
    kind: Literal["role", "achievement", "skill", "education", "certification"]
    text: str
    source_span: str | None = None  # where in the uploaded CV this came from


class CVChange(BaseModel):
    """One change in the tailored CV diff; every change cites its evidence."""

    section: str
    before: str | None = None
    after: str
    evidence_ids: list[str]  # must reference CVInventoryItem.id — validator enforces


class TailoredCV(BaseModel):
    job_id: str
    changes: list[CVChange]
    full_text: str
    needs_manual_edit: bool = False


class ValidationViolation(BaseModel):
    job_id: str
    change_index: int
    problem: str


class CopyAnswer(BaseModel):
    """Copy-ready application answer for the mobile Application Pack."""

    field: Literal[
        "notice_period",
        "salary_expectation",
        "right_to_work",
        "sponsorship",
        "why_this_company",
    ]
    text: str


class ApplicationPack(BaseModel):
    job_id: str
    tailored_cv: TailoredCV
    answers: list[CopyAnswer]
    apply_url: str  # deep link to the employer's application page
