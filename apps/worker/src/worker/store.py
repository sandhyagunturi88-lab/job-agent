"""Job store: upserts into the normalised `jobs` table and `job_chunks` index.

`PostgresJobStore` talks to Supabase (service role, bypasses RLS).
`MemoryJobStore` gives dev/tests the same contract with no database.
Upserts are keyed on Job.id, so re-running ingestion is idempotent.
"""

from typing import Protocol

from jobpilot_schemas import Job

Chunk = tuple[int, str, list[float]]  # (chunk_index, content, embedding)


class JobStore(Protocol):
    async def upsert_jobs(self, jobs: list[Job]) -> int: ...

    async def jobs_missing_chunks(self) -> list[Job]: ...

    async def upsert_chunks(self, job_id: str, chunks: list[Chunk]) -> None: ...


class MemoryJobStore:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.chunks: dict[str, list[Chunk]] = {}

    async def upsert_jobs(self, jobs: list[Job]) -> int:
        for job in jobs:
            self.jobs[job.id] = job
        return len(jobs)

    async def jobs_missing_chunks(self) -> list[Job]:
        return [job for job_id, job in self.jobs.items() if job_id not in self.chunks]

    async def upsert_chunks(self, job_id: str, chunks: list[Chunk]) -> None:
        self.chunks[job_id] = chunks


_JOB_COLUMNS = (
    "id, title, company, location, salary_min, salary_max, "
    "contract_type, ir35_flag, source, url, jd_text, posted_at"
)

_UPSERT_JOB = f"""
insert into public.jobs ({_JOB_COLUMNS})
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
on conflict (id) do update set
    title = excluded.title,
    company = excluded.company,
    location = excluded.location,
    salary_min = excluded.salary_min,
    salary_max = excluded.salary_max,
    contract_type = excluded.contract_type,
    ir35_flag = excluded.ir35_flag,
    url = excluded.url,
    jd_text = excluded.jd_text,
    posted_at = excluded.posted_at
"""

_MISSING_CHUNKS = f"""
select {_JOB_COLUMNS} from public.jobs j
where not exists (select 1 from public.job_chunks c where c.job_id = j.id)
"""

_UPSERT_CHUNK = """
insert into public.job_chunks (job_id, chunk_index, content, embedding)
values (%s, %s, %s, %s::vector)
on conflict (job_id, chunk_index) do update set
    content = excluded.content,
    embedding = excluded.embedding
"""


class PostgresJobStore:
    """Requires `pip install jobpilot-worker[postgres]` and DATABASE_URL."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _connect(self):
        import psycopg

        return psycopg.AsyncConnection.connect(self.database_url)

    async def upsert_jobs(self, jobs: list[Job]) -> int:
        async with await self._connect() as conn:
            async with conn.cursor() as cur:
                for j in jobs:
                    await cur.execute(
                        _UPSERT_JOB,
                        (
                            j.id, j.title, j.company, j.location, j.salary_min,
                            j.salary_max, j.contract_type, j.ir35_flag, j.source,
                            j.url, j.jd_text, j.posted_at,
                        ),
                    )
            await conn.commit()
        return len(jobs)

    async def jobs_missing_chunks(self) -> list[Job]:
        async with await self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_MISSING_CHUNKS)
                rows = await cur.fetchall()
        cols = [c.strip() for c in _JOB_COLUMNS.split(",")]
        return [Job(**dict(zip(cols, row, strict=True))) for row in rows]

    async def upsert_chunks(self, job_id: str, chunks: list[Chunk]) -> None:
        async with await self._connect() as conn:
            async with conn.cursor() as cur:
                for index, content, embedding in chunks:
                    vector_literal = "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"
                    await cur.execute(_UPSERT_CHUNK, (job_id, index, content, vector_literal))
            await conn.commit()


def make_store(database_url: str) -> JobStore:
    return PostgresJobStore(database_url) if database_url else MemoryJobStore()
