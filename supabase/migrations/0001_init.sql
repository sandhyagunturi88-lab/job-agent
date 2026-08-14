-- JobPilot UK — core schema.
-- Supabase project must be in AWS eu-west-2 (London): all user data resides in the UK.

create extension if not exists vector;
create extension if not exists pg_trgm;

-- ---------------------------------------------------------------------------
-- Per-user data (RLS: strict per-user row isolation)
-- ---------------------------------------------------------------------------

create table public.profiles (
    user_id uuid primary key references auth.users (id) on delete cascade,
    email text,
    plan text not null default 'free' check (plan in ('free', 'pro')),
    -- PreferenceProfile JSON (desired_titles, locations, min_salary,
    -- contract_types, avoid_keywords grown by learn_preferences, notes)
    preference_profile jsonb not null default '{}'::jsonb,
    cv_storage_path text, -- Supabase Storage object (bucket `cvs`, encrypted at rest)
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.cv_inventory (
    id text not null,
    user_id uuid not null references auth.users (id) on delete cascade,
    kind text not null check (kind in ('role', 'achievement', 'skill', 'education', 'certification')),
    text text not null,
    source_span text,
    created_at timestamptz not null default now(),
    primary key (user_id, id)
);

create table public.matches (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users (id) on delete cascade,
    run_date date not null,
    job_id text not null,
    score int not null check (score between 0 and 100),
    matched_skills jsonb not null default '[]'::jsonb,
    gaps jsonb not null default '[]'::jsonb,
    verdict text not null default '',
    status text not null default 'proposed'
        check (status in ('proposed', 'selected', 'dismissed')),
    dismissal_reason text,
    created_at timestamptz not null default now(),
    -- Idempotency: re-triggering a day's run never duplicates matches
    unique (user_id, run_date, job_id)
);

create table public.applications (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users (id) on delete cascade,
    job_id text not null,
    tailored_cv jsonb not null,       -- TailoredCV (changes carry evidence_ids)
    application_pack jsonb,           -- ApplicationPack (answers + apply_url)
    status text not null default 'pack_ready'
        check (status in ('pack_ready', 'applied', 'interviewing', 'offer', 'rejected', 'withdrawn')),
    applied_at timestamptz,           -- set when the user reports pressing submit
    created_at timestamptz not null default now(),
    unique (user_id, job_id)
);

-- Token usage per node per user (quality bar: cost visibility + quota)
create table public.usage (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users (id) on delete cascade,
    run_date date not null,
    node text not null,               -- 'llm_rerank' | 'tailor_cv' (the only LLM nodes)
    model text not null,
    input_tokens int not null default 0,
    output_tokens int not null default 0,
    created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.cv_inventory enable row level security;
alter table public.matches enable row level security;
alter table public.applications enable row level security;
alter table public.usage enable row level security;

create policy "own profile" on public.profiles
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own cv inventory" on public.cv_inventory
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own matches" on public.matches
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own applications" on public.applications
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own usage, read-only" on public.usage
    for select using (auth.uid() = user_id);

-- ---------------------------------------------------------------------------
-- Global job store (written by the worker via service role; readable by all
-- authenticated users — job postings are public data)
-- ---------------------------------------------------------------------------

create table public.jobs (
    id text primary key,
    title text not null,
    company text not null,
    location text not null,
    salary_min int,
    salary_max int,
    contract_type text check (contract_type in
        ('permanent', 'contract', 'temporary', 'part_time', 'internship')),
    ir35_flag boolean,
    source text not null check (source in
        ('adzuna', 'reed', 'dwp_find_a_job', 'greenhouse', 'lever', 'workable')),
    url text not null,
    jd_text text not null,
    posted_at timestamptz not null,
    ingested_at timestamptz not null default now(),
    -- Postgres full-text half of the hybrid search
    jd_tsv tsvector generated always as
        (to_tsvector('english', title || ' ' || company || ' ' || jd_text)) stored
);

create index jobs_jd_tsv_idx on public.jobs using gin (jd_tsv);
create index jobs_posted_at_idx on public.jobs (posted_at desc);
create index jobs_title_trgm_idx on public.jobs using gin (title gin_trgm_ops); -- fuzzy dedupe

create table public.job_chunks (
    id bigint generated always as identity primary key,
    job_id text not null references public.jobs (id) on delete cascade,
    chunk_index int not null,
    content text not null,
    -- pgvector half of the hybrid search; 1536 dims (embedding model fixed in phase 2)
    embedding vector(1536),
    unique (job_id, chunk_index)
);

create index job_chunks_embedding_idx on public.job_chunks
    using hnsw (embedding vector_cosine_ops);

alter table public.jobs enable row level security;
alter table public.job_chunks enable row level security;

create policy "jobs readable by authenticated" on public.jobs
    for select to authenticated using (true);
create policy "job chunks readable by authenticated" on public.job_chunks
    for select to authenticated using (true);
-- Writes to jobs/job_chunks happen only via the service role (worker), which bypasses RLS.
