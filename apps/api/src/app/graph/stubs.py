"""Deterministic phase-1 stand-ins for retrieval, reranking and tailoring.

Phase 2 replaces `hybrid_search` with pgvector cosine + Postgres full-text over
chunked JDs. Phase 3 replaces `rerank`/`tailor` with single batched Claude calls
(the ONLY two LLM call sites in the graph). Keeping these behind plain functions
lets tests monkeypatch them and keeps the graph shape final from day one.
"""

from datetime import datetime, timezone

from jobpilot_schemas import (
    CopyAnswer,
    CVChange,
    CVInventoryItem,
    Job,
    JobMatch,
    PreferenceProfile,
    TailoredCV,
    ValidationViolation,
)

_POSTED = datetime(2026, 8, 13, 9, 0, tzinfo=timezone.utc)

SAMPLE_JOBS: list[Job] = [
    Job(
        id="job-adzuna-001",
        title="Senior Python Engineer",
        company="Monzo",
        location="London (hybrid)",
        salary_min=85000,
        salary_max=105000,
        contract_type="permanent",
        source="adzuna",
        url="https://example.org/jobs/monzo-senior-python",
        jd_text=(
            "We need a senior Python engineer with FastAPI, Postgres and AWS "
            "experience to build payments infrastructure. Kubernetes a plus."
        ),
        posted_at=_POSTED,
    ),
    Job(
        id="job-reed-002",
        title="Backend Engineer (Python)",
        company="Starling Bank",
        location="London",
        salary_min=75000,
        salary_max=95000,
        contract_type="permanent",
        source="reed",
        url="https://example.org/jobs/starling-backend",
        jd_text=(
            "Backend engineer working on Python microservices, Postgres, Redis "
            "and event-driven systems in a regulated environment."
        ),
        posted_at=_POSTED,
    ),
    Job(
        id="job-gh-003",
        title="Machine Learning Engineer",
        company="DeepJudge",
        location="Remote (UK)",
        salary_min=90000,
        salary_max=120000,
        contract_type="permanent",
        source="greenhouse",
        url="https://example.org/jobs/deepjudge-mle",
        jd_text=(
            "ML engineer building LLM-powered retrieval systems. Python, "
            "embeddings, vector databases, evaluation pipelines."
        ),
        posted_at=_POSTED,
    ),
    Job(
        id="job-lever-004",
        title="Platform Engineer (Contract, Outside IR35)",
        company="Zopa",
        location="London",
        salary_min=None,
        salary_max=None,
        contract_type="contract",
        ir35_flag=False,
        source="lever",
        url="https://example.org/jobs/zopa-platform",
        jd_text="Contract platform engineer: Terraform, AWS, CI/CD, some Python tooling.",
        posted_at=_POSTED,
    ),
    Job(
        id="job-dwp-005",
        title="Junior Web Developer",
        company="Norfolk County Council",
        location="Norwich",
        salary_min=28000,
        salary_max=32000,
        contract_type="permanent",
        source="dwp_find_a_job",
        url="https://example.org/jobs/norfolk-webdev",
        jd_text="Junior developer maintaining PHP and WordPress sites for the council.",
        posted_at=_POSTED,
    ),
]

SAMPLE_INVENTORY: list[CVInventoryItem] = [
    CVInventoryItem(
        id="inv-1",
        kind="role",
        text="Senior Backend Engineer at FinCo, 2022-2026: Python services on AWS",
        source_span="cv p1 ¶2",
    ),
    CVInventoryItem(
        id="inv-2",
        kind="achievement",
        text="Cut p99 API latency 40% by moving hot paths to async FastAPI + Postgres",
        source_span="cv p1 ¶3",
    ),
    CVInventoryItem(
        id="inv-3",
        kind="achievement",
        text="Built an embeddings-based document search used by 3 internal teams",
        source_span="cv p2 ¶1",
    ),
    CVInventoryItem(id="inv-4", kind="skill", text="Python, FastAPI, Postgres, Redis, AWS"),
    CVInventoryItem(id="inv-5", kind="skill", text="Kubernetes, Terraform, CI/CD"),
    CVInventoryItem(
        id="inv-6", kind="education", text="BSc Computer Science, University of Manchester, 2018"
    ),
]

DEFAULT_PROFILE = PreferenceProfile(
    desired_titles=["Senior Python Engineer", "Backend Engineer", "ML Engineer"],
    locations=["London", "Remote (UK)"],
    min_salary=70000,
    contract_types=["permanent"],
)


def load_user_context(user_id: str) -> tuple[PreferenceProfile, list[CVInventoryItem]]:
    """Phase 2: read from Supabase (profiles + cv_inventory tables)."""
    return DEFAULT_PROFILE, SAMPLE_INVENTORY


def hybrid_search(
    profile: PreferenceProfile, cv_inventory: list[CVInventoryItem], top_k: int = 50
) -> list[Job]:
    """Phase 2: pgvector cosine + Postgres full-text over chunked JDs."""
    avoided = [kw.lower() for kw in profile.avoid_keywords]
    jobs = [j for j in SAMPLE_JOBS if not any(kw in j.jd_text.lower() for kw in avoided)]
    return jobs[:top_k]


def rerank(
    jobs: list[Job], profile: PreferenceProfile, cv_inventory: list[CVInventoryItem]
) -> list[JobMatch]:
    """Phase 3: single batched Claude call. Stub: keyword-overlap scoring."""
    cv_terms = {
        t.strip(".,").lower() for item in cv_inventory for t in item.text.replace(",", " ").split()
    }
    matches: list[JobMatch] = []
    for job in jobs:
        jd_terms = {t.strip(".,:").lower() for t in job.jd_text.split()}
        overlap = sorted(t for t in (cv_terms & jd_terms) if len(t) > 3)
        score = min(100, 20 + len(overlap) * 10)
        if profile.min_salary and job.salary_max and job.salary_max < profile.min_salary:
            score = max(0, score - 40)
        gaps = sorted(
            t
            for t in ("kubernetes", "terraform", "php", "wordpress")
            if t in jd_terms and t not in cv_terms
        )
        matches.append(
            JobMatch(
                job=job,
                score=score,
                matched_skills=overlap[:8],
                gaps=gaps,
                verdict=(
                    f"{'Strong' if score >= 60 else 'Partial'} fit "
                    f"on {len(overlap)} overlapping skills"
                ),
            )
        )
    return sorted(matches, key=lambda m: m.score, reverse=True)


def tailor(
    job: Job,
    cv_inventory: list[CVInventoryItem],
    edit_requests: str = "",
    violations: list[ValidationViolation] | None = None,
) -> TailoredCV:
    """Phase 3: Claude call constrained to the CV inventory. Stub: reorders the
    inventory so items overlapping the JD lead, every change citing evidence."""
    jd_lower = job.jd_text.lower()
    relevant = [
        item
        for item in cv_inventory
        if any(len(w) > 3 and w in jd_lower for w in item.text.lower().split())
    ] or cv_inventory[:2]
    changes = [
        CVChange(
            section="Profile" if item.kind == "role" else "Experience",
            before=None,
            after=item.text,
            evidence_ids=[item.id],
        )
        for item in relevant[:4]
    ]
    full_text = "\n".join(c.after for c in changes)
    return TailoredCV(job_id=job.id, changes=changes, full_text=full_text)


def copy_answers(job: Job, profile: PreferenceProfile) -> list[CopyAnswer]:
    """Copy-ready answers for the mobile Application Pack (phase 3 personalises)."""
    return [
        CopyAnswer(field="notice_period", text="One month"),
        CopyAnswer(
            field="salary_expectation",
            text=f"£{profile.min_salary or 0:,}+ depending on total package",
        ),
        CopyAnswer(field="right_to_work", text="Yes — full right to work in the UK"),
        CopyAnswer(field="sponsorship", text="No sponsorship required"),
        CopyAnswer(
            field="why_this_company",
            text=f"{job.company}'s work aligns with my background: {job.title.lower()} "
            "is exactly the kind of role where my recent experience applies directly.",
        ),
    ]
