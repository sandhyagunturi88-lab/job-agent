import type { CVInventoryItem } from "@jobpilot/schemas";
import { useEffect, useState } from "react";
import Sheet from "../components/Sheet";
import { cvBuilderUrl, getInventory, type useRun } from "../lib/api";

export default function CVDiffScreen({ run }: { run: ReturnType<typeof useRun> }) {
  const { snapshot, busy, resume } = run;
  const [evidenceFor, setEvidenceFor] = useState<string | null>(null);
  const [inventory, setInventory] = useState<Map<string, CVInventoryItem>>(new Map());
  const [editsOpen, setEditsOpen] = useState(false);
  const [editText, setEditText] = useState("");

  const approving = snapshot?.interrupt?.type === "approve_cv";

  useEffect(() => {
    if (!approving) return;
    void getInventory()
      .then((items) => setInventory(new Map(items.map((i) => [i.id, i]))))
      .catch(() => {});
  }, [approving]);

  if (snapshot?.interrupt?.type !== "approve_cv") {
    return (
      <div className="space-y-3">
        <p className="rounded-2xl bg-white p-4 text-sm text-slate-600 shadow-sm">
          Nothing to review yet — once you pick jobs on the Today tab, the tailored CV diff
          appears here for your approval.
        </p>
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold">Need a CV from scratch?</h3>
          <p className="mt-1 text-sm text-slate-500">
            CV Studio is JobPilot's guided builder — step-by-step form, live preview, and
            PDF/Word export. Built for first CVs and school leavers, useful for anyone.
          </p>
          <a
            href={cvBuilderUrl}
            target="_blank"
            rel="noreferrer"
            className="mt-3 block w-full rounded-xl bg-slate-100 py-2.5 text-center text-sm font-semibold text-slate-700"
          >
            Open CV Studio →
          </a>
        </div>
      </div>
    );
  }

  const { tailored_cvs: cvs, jobs } = snapshot.interrupt;

  const sendEdits = () => {
    if (!editText.trim()) return;
    setEditsOpen(false);
    void resume({ approved: false, edit_requests: editText.trim() });
  };

  return (
    <div className="space-y-3">
      <div className="rounded-2xl bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold">Review your tailored CV</h2>
        <p className="mt-1 text-sm text-slate-500">
          Every change is built only from your own CV — nothing is invented. Tap{" "}
          <span aria-hidden>ⓘ</span> to see the exact evidence behind a change.
        </p>
      </div>

      {cvs.map((cv) => {
        const job = jobs?.[cv.job_id];
        return (
          <div key={cv.job_id} className="rounded-2xl bg-white p-4 shadow-sm">
            <h3 className="font-semibold leading-snug">{job?.title ?? cv.job_id}</h3>
            {job && (
              <p className="text-sm text-slate-500">
                {job.company} · {job.location}
              </p>
            )}
            {cv.needs_manual_edit && (
              <p className="mt-2 rounded-lg bg-amber-50 p-2.5 text-xs text-amber-700">
                Some auto-tailored content failed the evidence check and was removed — please
                review and edit manually before applying.
              </p>
            )}

            <ul className="mt-3 space-y-2">
              {cv.changes.map((change, i) => {
                const key = `${cv.job_id}:${i}`;
                const evidence = change.evidence_ids
                  .map((id) => inventory.get(id))
                  .filter((x): x is CVInventoryItem => Boolean(x));
                return (
                  <li key={key} className="rounded-xl border border-slate-100 p-3 text-sm">
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                        {change.section}
                      </span>
                      <button
                        aria-label="Show evidence for this change"
                        aria-expanded={evidenceFor === key}
                        onClick={() => setEvidenceFor(evidenceFor === key ? null : key)}
                        className="rounded-full px-1.5 text-brand-600"
                      >
                        ⓘ
                      </button>
                    </div>
                    {change.before && (
                      <p className="mt-1 text-slate-400 line-through">{change.before}</p>
                    )}
                    <p className="mt-1 rounded-lg bg-emerald-50 p-2 text-emerald-900">
                      {change.after}
                    </p>
                    {evidenceFor === key && (
                      <div className="mt-2 rounded-lg bg-slate-50 p-2.5">
                        <p className="text-xs font-semibold text-slate-500">
                          From your master CV:
                        </p>
                        {evidence.length > 0 ? (
                          <ul className="mt-1 space-y-1">
                            {evidence.map((item) => (
                              <li key={item.id} className="text-xs text-slate-600">
                                <span className="mr-1 rounded bg-slate-200 px-1 py-0.5 font-mono text-[10px]">
                                  {item.kind}
                                </span>
                                {item.text}
                                {item.source_span && (
                                  <span className="text-slate-400"> ({item.source_span})</span>
                                )}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="mt-1 text-xs text-slate-500">
                            {change.evidence_ids.join(", ")} from your master CV inventory.
                          </p>
                        )}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}

      <div className="flex gap-2">
        <button
          onClick={() => void resume({ approved: true })}
          disabled={busy}
          className="flex-1 rounded-xl bg-brand-600 py-3 font-semibold text-white disabled:opacity-50"
        >
          {busy ? "Working…" : "Approve CV"}
        </button>
        <button
          onClick={() => setEditsOpen(true)}
          disabled={busy}
          className="rounded-xl bg-slate-200 px-4 py-3 font-medium disabled:opacity-50"
        >
          Request edits
        </button>
      </div>

      <Sheet open={editsOpen} title="What should change?" onClose={() => setEditsOpen(false)}>
        <p className="mb-3 text-sm text-slate-500">
          The CV will be re-tailored with your notes — still only from evidenced facts.
        </p>
        <textarea
          value={editText}
          onChange={(e) => setEditText(e.target.value)}
          rows={4}
          className="w-full rounded-lg border border-slate-300 p-3 text-sm"
          placeholder="e.g. lead with the payments migration project, drop the teaching role"
        />
        <button
          onClick={sendEdits}
          disabled={!editText.trim()}
          className="mt-3 w-full rounded-xl bg-brand-600 py-3 font-semibold text-white disabled:opacity-50"
        >
          Send edit requests
        </button>
      </Sheet>
    </div>
  );
}
