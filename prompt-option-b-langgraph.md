# Claude Code Build Prompt — Option B: LangGraph + RAG Design

Paste everything below the line into Claude Code. Fill [APP NAME] first.

---

You are building **[APP NAME]**, a paid personal job-agent SaaS for the UK market. Users upload their CV once; the system finds matching UK jobs daily via RAG, explains fit, tailors their CV per job with an evidence-only guarantee, gets human approval at two checkpoints, then autofills the application — the user always presses the final submit button. There is NO auto-submission anywhere in this product.

## Architecture (follow exactly — see attached diagram option-b-langgraph-light.mermaid)
Runtime pattern: **LangGraph StateGraph** with a Postgres checkpointer. One graph run per user per day (or on demand). Nodes:

`retrieve` → `llm_rerank` → **interrupt: user picks jobs** → `tailor_cv` → **interrupt: user approves CV diff** → `build_application_pack` → end
Rejection branch: interrupt 1 with a dismissal reason routes to `learn_preferences`, which updates the user profile used by future retrieve/rerank runs.

Rules:
- Use `interrupt()` + Postgres checkpointer (langgraph-checkpoint-postgres) so a run survives app closes, deploys and restarts — a user can pick jobs on the train and approve the CV that evening, resuming mid-graph
- `retrieve`: hybrid search (pgvector cosine + Postgres full-text) over chunked JDs against the user's chunked CV + preference profile, top 50
- `llm_rerank`: single batched Claude call scoring each job 0–100 with matched skills, gaps, and a one-line verdict; LLM calls happen ONLY in rerank and tailor nodes (cost control)
- `tailor_cv`: generates from the user's master CV inventory only; a deterministic validator node blocks any claim not evidenced in the inventory — failed validation loops back to tailor with the violation list, max 2 retries, then flags for manual edit

## Stack
- Backend: Python 3.12, FastAPI, LangGraph, langchain-anthropic (Claude for rerank + tailoring), WebSocket for graph state updates to the client
- Data: Postgres + pgvector via Supabase (also hosts the LangGraph checkpointer tables), Supabase Auth, Supabase Storage for CVs (encrypted at rest)
- Ingestion workers: scheduled pulls from Adzuna API, Reed.co.uk API, DWP Find a Job, public ATS boards (Greenhouse/Lever/Workable JSON). One normalised schema: title, company, location, salary_min/max, contract_type, ir35_flag, source, url, jd_text, posted_at. Fuzzy dedupe. Embedding worker chunks and indexes new JDs.
- Queue: Upstash Redis + arq
- Frontend: React 18 + Vite + TypeScript + Tailwind, installable PWA, mobile-first at 390px, bottom tabs
- Desktop autofill: Chrome extension (Manifest V3) filling Greenhouse/Lever/Workday/Workable forms from the Application Pack; highlights filled fields; user submits
- Mobile autofill substitute: **Application Pack** screen — tailored CV download + copy-ready answers (notice period, salary, right-to-work, sponsorship, "why this company") with one-tap copy + deep link to the employer's application page

## Hosting & deployment (build the config files)
- Frontend: **Vercel**
- Backend + workers: **Fly.io, region `lhr` (London)** — `fly.toml` for API app and worker app; the API app must NOT scale to zero (WebSocket + resumable graph runs)
- Database/auth/storage/checkpointer: **Supabase in AWS eu-west-2 (London)** — all user data resides in the UK; write SQL migrations + RLS policies (per-user row isolation)
- Redis: **Upstash EU**
- CI: GitHub Actions — lint, tests, deploy to Fly on main
- `PRIVACY.md`: data residency London, CV deletion 30 days after account deletion, UK GDPR endpoints `GET /api/v1/me/export` and `DELETE /api/v1/me`

## Human-in-the-loop flow (non-negotiable)
1. Daily graph run produces ranked matches with fit score + reasoning
2. **Interrupt 1 — user picks jobs**; dismissals capture a reason → learn_preferences
3. Graph tailors CV → **interrupt 2 — user reviews inline diff** (every change carries a tap-to-see evidence note), approves or requests edits (routes back to tailor node)
4. Application Pack built → autofill via extension (desktop) or copy-pack (mobile) → **user presses submit on the employer's site**
5. Applied status written to tracker

## Build phases (commit and show me a working state after each)
1. Monorepo scaffold (apps/web, apps/api, apps/worker, apps/extension, packages/schemas), Supabase migrations incl. checkpointer tables, Fly + Vercel config
2. Ingestion + normalised job store + embedding worker (API keys behind an interface, mocked until I supply real keys)
3. The full StateGraph with both interrupts, checkpointer resume tests (kill the process mid-run, resume, assert state), validator unit tests proving fabricated claims are blocked
4. PWA screens: onboarding (CV upload + preferences + plan), Today feed, job detail, CV diff approval, Application Pack, tracker — driven live by graph state over WebSocket
5. Chrome extension autofill for Greenhouse + Lever first
6. Stripe billing (Free: 5 matches/week, 1 tailored CV; Pro £X/mo unlimited) with webhooks

## Quality bar
- Token usage logged per node per user to a `usage` table
- Graph runs idempotent: re-triggering a day's run never duplicates matches or double-charges quota
- Lighthouse mobile ≥ 90; WCAG AA; prefers-reduced-motion respected
- No dark patterns in the paywall

Start with phase 1. Before writing code, output a short plan and the repo tree for my approval.
