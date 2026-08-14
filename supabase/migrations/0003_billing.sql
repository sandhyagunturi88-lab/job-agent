-- Phase 6: billing. Stripe customer linkage + weekly quota tracking.

alter table public.profiles add column if not exists stripe_customer_id text;
create index if not exists profiles_stripe_customer_idx
    on public.profiles (stripe_customer_id) where stripe_customer_id is not null;

-- Quota is recorded per graph thread (one thread = one user-day run), so
-- re-triggering a day's run can never double-charge quota: writes use
-- GREATEST(existing, new), and the (user_id, thread_id) key absorbs retries.
create table public.quota_usage (
    user_id uuid not null references auth.users (id) on delete cascade,
    thread_id text not null,
    week text not null,          -- ISO week bucket, e.g. '2026-W33' (Monday-based)
    matches int not null default 0,  -- matches shown at the pick_jobs interrupt
    cvs int not null default 0,      -- CVs tailored for this thread
    created_at timestamptz not null default now(),
    primary key (user_id, thread_id)
);

create index quota_usage_week_idx on public.quota_usage (user_id, week);

alter table public.quota_usage enable row level security;

create policy "own quota, read-only" on public.quota_usage
    for select using (auth.uid() = user_id);
-- Writes happen via the API service role only.
