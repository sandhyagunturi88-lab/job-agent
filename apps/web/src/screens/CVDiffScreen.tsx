import { useState } from "react";
import type { useRun } from "../lib/api";

export default function CVDiffScreen({ run }: { run: ReturnType<typeof useRun> }) {
  const { snapshot, busy, resume } = run;
  const [evidenceFor, setEvidenceFor] = useState<string | null>(null);

  if (snapshot?.interrupt?.type !== "approve_cv") {
    return (
      <p className="rounded-2xl bg-white p-4 text-sm text-slate-600 shadow-sm">
        Nothing to review yet — once you pick jobs, the tailored CV diff appears here.
      </p>
    );
  }

  const cvs = snapshot.interrupt.tailored_cvs;

  const requestEdits = () => {
    const edits = window.prompt("What should change?") ?? "";
    if (edits) void resume({ approved: false, edit_requests: edits });
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        Review every change. Each one is backed by evidence from your own CV — nothing is
        invented. Tap ⓘ to see the evidence.
      </p>
      {cvs.map((cv) => (
        <div key={cv.job_id} className="rounded-2xl bg-white p-4 shadow-sm">
          <h3 className="font-semibold">For {cv.job_id}</h3>
          {cv.needs_manual_edit && (
            <p className="mt-1 rounded-lg bg-amber-50 p-2 text-xs text-amber-700">
              Some auto-tailored content failed the evidence check and was removed — please
              review and edit manually.
            </p>
          )}
          <ul className="mt-2 space-y-2">
            {cv.changes.map((change, i) => {
              const key = `${cv.job_id}:${i}`;
              return (
                <li key={key} className="rounded-lg bg-emerald-50 p-2 text-sm">
                  <div className="flex items-start justify-between gap-2">
                    <span>
                      <span className="text-xs font-semibold uppercase text-emerald-700">
                        {change.section}:
                      </span>{" "}
                      {change.after}
                    </span>
                    <button
                      aria-label="Show evidence"
                      onClick={() => setEvidenceFor(evidenceFor === key ? null : key)}
                      className="text-brand-600"
                    >
                      ⓘ
                    </button>
                  </div>
                  {evidenceFor === key && (
                    <p className="mt-1 text-xs text-slate-500">
                      Evidence: {change.evidence_ids.join(", ")} from your master CV inventory.
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      ))}
      <div className="flex gap-2">
        <button
          onClick={() => void resume({ approved: true })}
          disabled={busy}
          className="flex-1 rounded-xl bg-brand-600 py-3 font-semibold text-white disabled:opacity-50"
        >
          Approve CV
        </button>
        <button
          onClick={requestEdits}
          disabled={busy}
          className="rounded-xl bg-slate-200 px-4 py-3 font-medium disabled:opacity-50"
        >
          Request edits
        </button>
      </div>
    </div>
  );
}
