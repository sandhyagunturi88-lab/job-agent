"""Hybrid retrieval: pgvector cosine + Postgres full-text over chunked JDs,
fused with Reciprocal Rank Fusion, top 50 distinct jobs.

Used by the retrieve node when DATABASE_URL is configured; dev/tests without a
database fall back to the deterministic stub corpus. The query is built from
the user's CV inventory + preference profile, embedded with the SAME model the
worker used to index chunks (jobpilot_schemas.embeddings).
"""

from jobpilot_schemas import CVInventoryItem, Job, PreferenceProfile
from jobpilot_schemas.embeddings import make_embedder

from app.core.config import get_settings

TOP_K = 50
RRF_K = 60  # standard reciprocal-rank-fusion constant
_CANDIDATES_PER_LEG = 100

_JOB_COLUMNS = (
    "id, title, company, location, salary_min, salary_max, "
    "contract_type, ir35_flag, source, url, jd_text, posted_at"
)

_HYBRID_SQL = f"""
with fts as (
    select j.id,
           row_number() over (
               order by ts_rank(j.jd_tsv, plainto_tsquery('english', %(query)s)) desc
           ) as rn
    from public.jobs j
    where j.jd_tsv @@ plainto_tsquery('english', %(query)s)
    limit {_CANDIDATES_PER_LEG}
),
vec as (
    select sub.id, row_number() over (order by sub.dist) as rn
    from (
        select c.job_id as id, min(c.embedding <=> %(embedding)s::vector) as dist
        from public.job_chunks c
        group by c.job_id
        order by dist
        limit {_CANDIDATES_PER_LEG}
    ) sub
),
fused as (
    select coalesce(fts.id, vec.id) as id,
           coalesce(1.0 / ({RRF_K} + fts.rn), 0) + coalesce(1.0 / ({RRF_K} + vec.rn), 0) as score
    from fts full outer join vec using (id)
)
select {_JOB_COLUMNS}
from fused join public.jobs using (id)
order by fused.score desc
limit %(top_k)s
"""


def build_query_text(profile: PreferenceProfile, cv_inventory: list[CVInventoryItem]) -> str:
    parts = [
        " ".join(profile.desired_titles),
        " ".join(profile.locations),
        " ".join(item.text for item in cv_inventory if item.kind in ("skill", "role")),
    ]
    return " ".join(p for p in parts if p)


def hybrid_search(
    profile: PreferenceProfile, cv_inventory: list[CVInventoryItem], top_k: int = TOP_K
) -> list[Job]:
    import psycopg

    settings = get_settings()
    query_text = build_query_text(profile, cv_inventory)
    embedder = make_embedder(settings.voyage_api_key, settings.voyage_model)
    [query_embedding] = embedder.embed([query_text], input_type="query")
    vector_literal = "[" + ",".join(f"{x:.6f}" for x in query_embedding) + "]"

    with psycopg.connect(settings.database_url) as conn:
        rows = conn.execute(
            _HYBRID_SQL,
            {"query": query_text, "embedding": vector_literal, "top_k": top_k},
        ).fetchall()

    columns = [c.strip() for c in _JOB_COLUMNS.split(",")]
    avoided = [kw.lower() for kw in profile.avoid_keywords]
    jobs = [Job(**dict(zip(columns, row, strict=True))) for row in rows]
    return [j for j in jobs if not any(kw in j.jd_text.lower() for kw in avoided)]
