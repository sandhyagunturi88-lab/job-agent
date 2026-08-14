import type { useRun } from "../lib/api";

export default function TrackerScreen({ run }: { run: ReturnType<typeof useRun> }) {
  const packs = run.snapshot?.values.application_packs ?? [];
  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600">
        Your applications. Phase 2 persists this to the tracker table; for now it reflects
        today's run.
      </p>
      {packs.length === 0 ? (
        <p className="rounded-2xl bg-white p-4 text-sm text-slate-500 shadow-sm">
          Nothing tracked yet.
        </p>
      ) : (
        packs.map((pack) => (
          <div
            key={pack.job_id}
            className="flex items-center justify-between rounded-2xl bg-white p-4 shadow-sm"
          >
            <span className="text-sm font-medium">{pack.job_id}</span>
            <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">
              pack ready
            </span>
          </div>
        ))
      )}
    </div>
  );
}
