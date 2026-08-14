# JobPilot UK — Privacy

## Data residency

All user data — account details, CVs, CV inventories, job matches, tailored CVs,
application packs and LangGraph checkpoints — is stored in **Supabase (AWS eu-west-2,
London)**. Compute runs on **Fly.io region `lhr` (London)** and queue state on
**Upstash Redis (EU)**. No user data is stored outside the UK/EU.

## What we store

- Your account (email, auth identity via Supabase Auth)
- Your uploaded CV files (Supabase Storage, encrypted at rest) and the structured
  **master CV inventory** derived from them
- Your job preferences and dismissal reasons (used only to improve your own matches)
- Job matches, tailored CVs, application packs and application tracker entries
- Per-node token usage for billing/quota (`usage` table)

## What we never do

- We never submit an application on your behalf. You always press the final submit
  button on the employer's site.
- We never fabricate CV content: tailored CVs are generated only from your own CV
  inventory and validated against it before you see them.
- We never sell or share your data with employers or third parties.

## Your UK GDPR rights

- **Export** everything we hold about you: `GET /api/v1/me/export` (JSON download,
  available in-app under Settings → Export my data)
- **Delete** your account and data: `DELETE /api/v1/me` (available in-app under
  Settings → Delete account)

On account deletion your rows are removed immediately; uploaded CV files are purged
from storage and backups within **30 days**.

## Sub-processors

Supabase (database, auth, storage — AWS eu-west-2), Fly.io (compute — lhr),
Upstash (Redis — EU), Anthropic (LLM calls for match reasoning and CV tailoring;
only the minimum job/CV text needed per call), Stripe (billing; card details never
touch our servers), Vercel (static frontend hosting).
