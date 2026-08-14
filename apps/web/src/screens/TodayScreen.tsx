import type { JobMatch } from "@jobpilot/schemas";
import { useState } from "react";
import { Link } from "react-router-dom";
import ScoreRing, { scoreBucket } from "../components/ScoreRing";
import Sheet from "../components/Sheet";
import type { useRun } from "../lib/api";

const DISMISS_REASONS = [
  "Salary too low",
  "Wrong location",
  "Wrong tech stack",
  "Too junior",
  "Too senior",
  "Company isn't right for me",
];

const greeting = () => {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
};

function SummaryCard({ matches }: { matches: JobMatch[] }) {
  const counts = { strong: 0, fair: 0, stretch: 0 };
  for (const m of matches) counts[scoreBucket(m.score)] += 1;
  const parts = [
    counts.strong && `${counts.strong} strong`,
    counts.fair && `${counts.fair} fair`,
    counts.stretch && `${counts.stretch} stretch`,
  ].filter(Boolean);
  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold">
        {greeting()} — {matches.length} match{matches.length === 1 ? "" : "es"} today
      </h2>
      {parts.length > 0 && <p className="mt-1 text-sm text-slate-500">{parts.join(" · ")}</p>}
    </div>
  );
}

const salaryLine = (m: JobMatch) => {
  const { salary_min, salary_max, contract_type, ir35_flag } = m.job;
  const fmt = (n: number) => `£${n >= 1000 ? `${Math.round(n / 1000)}k` : n}`;
  const bits = [];
  if (salary_min || salary_max)
    bits.push(
      salary_min && salary_max && salary_min !== salary_max
        ? `${fmt(salary_min)}–${fmt(salary_max)}`
        : fmt(salary_min ?? salary_max ?? 0),
    );
  if (contract_type) bits.push(contract_type.replace("_", " "));
  if (ir35_flag !== null && ir35_flag !== undefined)
    bits.push(ir35_flag ? "inside IR35" : "outside IR35");
  return bits.join(" · ");
};

function MatchCard({
  match,
  selected,
  onToggle,
  onDismiss,
}: {
  match: JobMatch;
  selected: boolean;
  onToggle: () => void;
  onDismiss: () => void;
}) {
  const m = match;
  return (
    <article
      className={`rounded-2xl border bg-white p-4 shadow-sm transition-colors ${
        selected ? "border-brand-500" : "border-transparent"
      }`}
    >
      <div className="flex items-start gap-3">
        <ScoreRing score={m.score} />
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold leading-snug">{m.job.title}</h3>
          <p className="truncate text-sm text-slate-500">
            {m.job.company} · {m.job.location}
          </p>
          {salaryLine(m) && <p className="text-xs text-slate-500">{salaryLine(m)}</p>}
        </div>
      </div>

      {m.verdict && <p className="mt-3 text-sm text-slate-600">“{m.verdict}”</p>}

      {(m.matched_skills.length > 0 || m.gaps.length > 0) && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {m.matched_skills.map((s) => (
            <span
              key={s}
              className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700"
            >
              ✓ {s}
            </span>
          ))}
          {m.gaps.map((g) => (
            <span key={g} className="rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
              △ {g}
            </span>
          ))}
        </div>
      )}

      <div className="mt-3 flex items-center gap-2">
        <button
          onClick={onToggle}
          aria-pressed={selected}
          className={`flex-1 rounded-lg py-2.5 text-sm font-medium ${
            selected ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-700"
          }`}
        >
          {selected ? "Picked ✓" : "Pick"}
        </button>
        <button
          onClick={onDismiss}
          className="rounded-lg bg-slate-100 px-3 py-2.5 text-sm text-slate-700"
        >
          Dismiss
        </button>
        <Link
          to={`/today/${m.job.id}`}
          className="rounded-lg px-2 py-2.5 text-sm font-medium text-brand-600"
        >
          Details
        </Link>
      </div>
    </article>
  );
}

export default function TodayScreen({ run }: { run: ReturnType<typeof useRun> }) {
  const { snapshot, loading, busy, error, start, resume } = run;
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [dismissed, setDismissed] = useState<Map<string, string>>(new Map());
  const [dismissTarget, setDismissTarget] = useState<JobMatch | null>(null);
  const [reason, setReason] = useState("");

  const picking = snapshot?.interrupt?.type === "pick_jobs";
  const matches = snapshot?.interrupt?.type === "pick_jobs" ? snapshot.interrupt.matches : [];
  const open = matches.filter((m) => !dismissed.has(m.job.id));

  const toggle = (jobId: string) => {
    const next = new Set(selected);
    next.has(jobId) ? next.delete(jobId) : next.add(jobId);
    setSelected(next);
  };

  const confirmDismiss = () => {
    if (!dismissTarget || !reason.trim()) return;
    setDismissed(new Map(dismissed).set(dismissTarget.job.id, reason.trim()));
    const next = new Set(selected);
    next.delete(dismissTarget.job.id);
    setSelected(next);
    setDismissTarget(null);
    setReason("");
  };

  const submitPicks = () =>
    resume({
      selected_job_ids: [...selected],
      dismissals: [...dismissed.entries()].map(([job_id, r]) => ({ job_id, reason: r })),
    });

  if (loading) {
    return <p className="rounded-2xl bg-white p-5 text-sm text-slate-500 shadow-sm">Checking today's run…</p>;
  }

  return (
    <div className="space-y-3">
      {error && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {!snapshot && (
        <div className="rounded-2xl bg-white p-6 shadow-sm">
          <h2 className="text-base font-semibold">
            {greeting()} — ready to find today's matches?
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            We search UK job boards, score each role against your CV, and wait for your picks at
            every step. Nothing is ever submitted for you.
          </p>
          <button
            onClick={start}
            disabled={busy}
            className="mt-4 w-full rounded-xl bg-brand-600 py-3 font-semibold text-white disabled:opacity-50"
          >
            {busy ? "Searching…" : "Run today's search"}
          </button>
        </div>
      )}

      {picking && (
        <>
          <SummaryCard matches={matches} />
          {open.map((m) => (
            <MatchCard
              key={m.job.id}
              match={m}
              selected={selected.has(m.job.id)}
              onToggle={() => toggle(m.job.id)}
              onDismiss={() => {
                setDismissTarget(m);
                setReason("");
              }}
            />
          ))}
          {dismissed.size > 0 && (
            <p className="text-center text-xs text-slate-400">
              {dismissed.size} dismissed — we'll avoid similar roles in future.
            </p>
          )}
          <div className="sticky bottom-0 -mx-4 bg-gradient-to-t from-slate-50 via-slate-50 px-4 pb-2 pt-3">
            <button
              onClick={submitPicks}
              disabled={busy || (selected.size === 0 && dismissed.size === 0)}
              className="w-full rounded-xl bg-brand-600 py-3 font-semibold text-white shadow-sm disabled:opacity-50"
            >
              {busy
                ? "Working…"
                : selected.size > 0
                  ? `Continue with ${selected.size} pick${selected.size === 1 ? "" : "s"}`
                  : "Finish — nothing today"}
            </button>
          </div>
        </>
      )}

      {snapshot && !picking && (
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          {snapshot.interrupt?.type === "approve_cv" ? (
            <>
              <h2 className="text-base font-semibold">Your tailored CV is ready</h2>
              <p className="mt-1 text-sm text-slate-500">
                Review every change — each one cites evidence from your own CV.
              </p>
              <Link
                to="/cv"
                className="mt-3 block w-full rounded-xl bg-brand-600 py-3 text-center font-semibold text-white"
              >
                Review CV changes
              </Link>
            </>
          ) : snapshot.phase === "done" ? (
            <>
              <h2 className="text-base font-semibold">Today's packs are ready 🎉</h2>
              <p className="mt-1 text-sm text-slate-500">
                Your tailored CV and copy-ready answers are in the Pack tab.
              </p>
              <Link
                to="/pack"
                className="mt-3 block w-full rounded-xl bg-brand-600 py-3 text-center font-semibold text-white"
              >
                Open Application Pack
              </Link>
            </>
          ) : (
            <p className="text-sm text-slate-600">
              Working on it — {snapshot.phase ?? "starting"}…
            </p>
          )}
        </div>
      )}

      <Sheet
        open={dismissTarget !== null}
        title={`Why isn't “${dismissTarget?.job.title}” right?`}
        onClose={() => setDismissTarget(null)}
      >
        <p className="mb-3 text-sm text-slate-500">
          Your reason teaches the matcher what to avoid tomorrow.
        </p>
        <div className="flex flex-wrap gap-2">
          {DISMISS_REASONS.map((r) => (
            <button
              key={r}
              onClick={() => setReason(r)}
              aria-pressed={reason === r}
              className={`rounded-full border px-3 py-1.5 text-sm ${
                reason === r
                  ? "border-brand-600 bg-brand-50 text-brand-700"
                  : "border-slate-200 text-slate-600"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
        <label className="mt-3 block text-sm text-slate-600">
          Or in your own words
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="e.g. contract is inside IR35"
          />
        </label>
        <button
          onClick={confirmDismiss}
          disabled={!reason.trim()}
          className="mt-4 w-full rounded-xl bg-brand-600 py-3 font-semibold text-white disabled:opacity-50"
        >
          Dismiss this job
        </button>
      </Sheet>
    </div>
  );
}
