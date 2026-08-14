# JobPilot UK

A paid personal job-agent SaaS for the UK market. Users upload their CV once; JobPilot finds
matching UK jobs daily via RAG, explains fit, tailors their CV per job with an
**evidence-only guarantee**, gets human approval at two checkpoints, then autofills the
application — **the user always presses the final submit button**. There is no
auto-submission anywhere in this product.

## Architecture

Runtime pattern: **LangGraph `StateGraph`** with a Postgres checkpointer
(`langgraph-checkpoint-postgres`). One graph run per user per day (or on demand):

```
retrieve → llm_rerank → [interrupt 1: user picks jobs] → tailor_cv → validate_cv
        → [interrupt 2: user approves CV diff] → build_application_pack → end
```

- Dismissals at interrupt 1 carry a reason and route through `learn_preferences`,
  which updates the profile used by future retrieve/rerank runs.
- `validate_cv` is deterministic: any tailored-CV claim not evidenced in the user's
  master CV inventory loops back to `tailor_cv` with the violation list (max 2 retries,
  then flagged for manual edit).
- LLM calls happen **only** in `llm_rerank` and `tailor_cv` (cost control).
- `interrupt()` + the Postgres checkpointer means a run survives app closes, deploys
  and restarts — pick jobs on the train, approve the CV that evening.

## Monorepo layout

```
apps/
  web/         React 18 + Vite + TS + Tailwind PWA (mobile-first 390px, bottom tabs)
  api/         FastAPI + LangGraph graph, WebSocket state stream
  worker/      arq workers: ingestion (Adzuna, Reed, DWP, ATS boards), dedupe, embeddings
  extension/   Chrome MV3 autofill (Greenhouse/Lever first)
packages/
  schemas/     Shared Pydantic models + TypeScript types (single source of truth)
supabase/
  migrations/  SQL: pgvector, normalised job store, RLS, checkpointer tables
infra/         fly.api.toml, fly.worker.toml, vercel.json
```

## Hosting

| Layer | Where |
|---|---|
| Frontend | Vercel |
| API + workers | Fly.io, region `lhr` (London); API never scales to zero |
| DB / auth / storage / checkpointer | Supabase in AWS `eu-west-2` (London) |
| Queue | Upstash Redis (EU) + arq |

All user data resides in the UK. See [PRIVACY.md](PRIVACY.md).

## Local development

Requirements: Python ≥ 3.12, Node ≥ 20.

```sh
# API
cd apps/api
py -m venv .venv && .venv/Scripts/activate      # or python3 -m venv on unix
pip install -e . -e ../../packages/schemas
pytest                                          # graph interrupt/resume + validator tests
uvicorn app.main:app --reload                   # http://localhost:8000

# Web
npm install                                     # from repo root (npm workspaces)
npm run dev --workspace apps/web                # http://localhost:5173

# Worker (needs Redis; mocked sources until real API keys are supplied)
cd apps/worker && pip install -e . -e ../../packages/schemas
arq worker.main.WorkerSettings
```

Without `DATABASE_URL` the API falls back to an in-memory checkpointer (dev/test only —
runs do not survive restarts). Copy `.env.example` to `.env` and fill what you have;
every external service sits behind an interface and is mocked until keys are provided.

## Build phases

1. ✅ Monorepo scaffold, Supabase migrations (incl. checkpointer tables), Fly + Vercel config
2. ✅ Ingestion + normalised job store + embedding worker (Adzuna/Reed/Greenhouse/Lever/
   Workable clients — mocked until credentials/watchlists are configured; Voyage AI
   embeddings behind `VOYAGE_API_KEY` with a deterministic dev fallback)
3. ✅ Full StateGraph on real infrastructure: Claude (claude-opus-5 via
   langchain-anthropic) in the two LLM nodes with structured outputs + per-node
   token usage logging, hybrid pgvector+FTS retrieval, SQLite dev checkpointer,
   and kill-the-process resume tests (fresh processes + kill -9 mid-node)
4. ✅ PWA screens driven live by graph state over WebSocket ("Daily Briefing"
   design): onboarding wizard (CV → evidence inventory via deterministic parser,
   preferences, honest plan picker), Today feed with fit-score rings and
   dismiss-reason sheets, job detail, CV diff approval with real evidence
   popovers, Application Pack with copy buttons, tracker with statuses
   (`/api/v1/me/*` endpoints; memory store without `DATABASE_URL`, Supabase
   tables with it)
5. ✅ Chrome extension autofill (Greenhouse + Lever, classic + React boards):
   auto-matches the open application page to a pack by URL, fills contact
   details + label-mapped custom questions (notice/salary/right-to-work/
   sponsorship/why-us, yes/no dropdowns handled), attaches the tailored CV
   as .txt, highlights every filled field — never overwrites what you typed,
   never submits. Fixture pages in `apps/extension/test-pages/`, pure mapping
   logic tested via `npm run test:extension`
6. ✅ Stripe billing: Free (5 matches/week, 1 tailored CV/week — Monday reset)
   vs Pro (£9/month, unlimited). Quotas enforced in the run lifecycle (402s
   with plain-English messages; the match cap is shown as "top N of M found",
   never silent) and recorded per thread so re-triggering a day's run never
   double-charges. Stripe checkout/portal via REST + signature-verified
   webhooks; without keys a mock provider exercises the whole
   upgrade/downgrade flow offline. No dark patterns: quota always visible,
   cancel is one click, Free stays useful forever.
