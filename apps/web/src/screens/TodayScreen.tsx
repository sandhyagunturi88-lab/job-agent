import type { useRun } from "../lib/api";
import { useState } from "react";

export default function TodayScreen({ run }: { run: ReturnType<typeof useRun> }) {
  const { snapshot, busy, error, start, resume } = run;
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [dismissed, setDismissed] = useState<Map<string, string>>(new Map());

  const picking = snapshot?.interrupt?.type === "pick_jobs";
  const matches = picking && snapshot?.interrupt?.type === "pick_jobs" ? snapshot.interrupt.matches : [];

  const toggle = (jobId: string) => {
    const next = new Set(selected);
    next.has(jobId) ? next.delete(jobId) : next.add(jobId);
    setSelected(next);
  };

  const dismiss = (jobId: string) => {
    const reason = window.prompt("Why isn't this one right? (helps future matches)") ?? "";
    if (!reason) return;
    setDismissed(new Map(dismissed).set(jobId, reason));
    const next = new Set(selected);
    next.delete(jobId);
    setSelected(next);
  };

  const submitPicks = () =>
    resume({
      selected_job_ids: [...selected],
      dismissals: [...dismissed.entries()].map(([job_id, reason]) => ({ job_id, reason })),
    });

  return (
    <div className="space-y-4">
      {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {!snapshot && (
        <div className="rounded-2xl bg-white p-6 text-center shadow-sm">
          <h2 className="text-base font-semibold">Find today's matches</h2>
          <p className="mt-1 text-sm text-slate-500">
            We search UK boards, score fit against your CV, and wait for your picks. Nothing is
            ever submitted for you.
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
          <p className="text-sm text-slate-600">
            {matches.length} matches — pick the ones worth applying to:
          </p>
          {matches.map((m) => {
            const isSelected = selected.has(m.job.id);
            const isDismissed = dismissed.has(m.job.id);
            return (
              <div
                key={m.job.id}
                className={`rounded-2xl border bg-white p-4 shadow-sm ${
                  isSelected ? "border-brand-500" : "border-transparent"
                } ${isDismissed ? "opacity-40" : ""}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-semibold">{m.job.title}</h3>
                    <p className="text-sm text-slate-500">
                      {m.job.company} · {m.job.location}
                    </p>
                  </div>
                  <span className="rounded-full bg-brand-50 px-2 py-1 text-xs font-bold text-brand-700">
                    {m.score}
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-600">{m.verdict}</p>
                {m.matched_skills.length > 0 && (
                  <p className="mt-1 text-xs text-slate-500">✓ {m.matched_skills.join(", ")}</p>
                )}
                {m.gaps.length > 0 && (
                  <p className="text-xs text-amber-600">△ gaps: {m.gaps.join(", ")}</p>
                )}
                {!isDismissed && (
                  <div className="mt-3 flex gap-2">
                    <button
                      onClick={() => toggle(m.job.id)}
                      className={`flex-1 rounded-lg py-2 text-sm font-medium ${
                        isSelected ? "bg-brand-600 text-white" : "bg-slate-100"
                      }`}
                    >
                      {isSelected ? "Picked ✓" : "Pick"}
                    </button>
                    <button
                      onClick={() => dismiss(m.job.id)}
                      className="rounded-lg bg-slate-100 px-3 py-2 text-sm"
                    >
                      Dismiss
                    </button>
                  </div>
                )}
              </div>
            );
          })}
          <button
            onClick={submitPicks}
            disabled={busy || (selected.size === 0 && dismissed.size === 0)}
            className="w-full rounded-xl bg-brand-600 py-3 font-semibold text-white disabled:opacity-50"
          >
            {busy ? "Working…" : `Continue with ${selected.size} pick${selected.size === 1 ? "" : "s"}`}
          </button>
        </>
      )}

      {snapshot && !picking && (
        <p className="rounded-2xl bg-white p-4 text-sm text-slate-600 shadow-sm">
          {snapshot.interrupt?.type === "approve_cv"
            ? "Your tailored CV is ready to review in the CV tab."
            : snapshot.phase === "done"
              ? "Today's packs are ready — see the Pack tab."
              : "Working on it…"}
        </p>
      )}
    </div>
  );
}
