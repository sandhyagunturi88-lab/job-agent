-- LangGraph Postgres checkpointer tables (langgraph-checkpoint-postgres v2).
--
-- The API also calls AsyncPostgresSaver.setup() on boot, which is the
-- authoritative source of this schema and records its own migration version in
-- checkpoint_migrations — this file exists so the tables are provisioned,
-- reviewable and RLS-locked alongside the rest of the schema. Keep in sync
-- with the installed langgraph-checkpoint-postgres version.
--
-- These tables are what make a graph run survive app closes, deploys and
-- restarts: a user can pick jobs on the train and approve the CV that evening.
-- thread_id format: "{user_id}:{run_date}".

create table if not exists public.checkpoint_migrations (
    v integer primary key
);

create table if not exists public.checkpoints (
    thread_id text not null,
    checkpoint_ns text not null default '',
    checkpoint_id text not null,
    parent_checkpoint_id text,
    type text,
    checkpoint jsonb not null,
    metadata jsonb not null default '{}'::jsonb,
    primary key (thread_id, checkpoint_ns, checkpoint_id)
);

create table if not exists public.checkpoint_blobs (
    thread_id text not null,
    checkpoint_ns text not null default '',
    channel text not null,
    version text not null,
    type text not null,
    blob bytea,
    primary key (thread_id, checkpoint_ns, channel, version)
);

create table if not exists public.checkpoint_writes (
    thread_id text not null,
    checkpoint_ns text not null default '',
    checkpoint_id text not null,
    task_id text not null,
    idx integer not null,
    channel text not null,
    type text,
    blob bytea not null,
    task_path text not null default '',
    primary key (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

create index if not exists checkpoints_thread_id_idx on public.checkpoints (thread_id);
create index if not exists checkpoint_blobs_thread_id_idx on public.checkpoint_blobs (thread_id);
create index if not exists checkpoint_writes_thread_id_idx on public.checkpoint_writes (thread_id);

-- Checkpoints contain user CV/match data. Only the backend (service role,
-- which bypasses RLS) may touch them; deny-all for anon/authenticated.
alter table public.checkpoints enable row level security;
alter table public.checkpoint_blobs enable row level security;
alter table public.checkpoint_writes enable row level security;
alter table public.checkpoint_migrations enable row level security;
