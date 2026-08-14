import { useCallback, useEffect, useState } from "react";
import PlanCard from "../components/PlanCard";
import Sheet from "../components/Sheet";
import {
  type ApplicationRow,
  getApplications,
  setApplicationStatus,
  type useRun,
} from "../lib/api";

const STATUS_LABELS: Record<string, string> = {
  pack_ready: "Pack ready",
  applied: "Applied",
  interviewing: "Interviewing",
  offer: "Offer 🎉",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

const STATUS_STYLE: Record<string, string> = {
  pack_ready: "bg-brand-50 text-brand-700",
  applied: "bg-emerald-50 text-emerald-700",
  interviewing: "bg-amber-50 text-amber-700",
  offer: "bg-emerald-100 text-emerald-800",
  rejected: "bg-slate-100 text-slate-500",
  withdrawn: "bg-slate-100 text-slate-500",
};

export default function TrackerScreen({ run }: { run: ReturnType<typeof useRun> }) {
  const [rows, setRows] = useState<ApplicationRow[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [editing, setEditing] = useState<ApplicationRow | null>(null);

  const refresh = useCallback(() => {
    void getApplications()
      .then(setRows)
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, []);

  // refresh when today's run finishes (packs are recorded server-side)
  const phase = run.snapshot?.phase;
  useEffect(() => {
    refresh();
  }, [refresh, phase]);

  const updateStatus = async (status: string) => {
    if (!editing) return;
    setEditing(null);
    await setApplicationStatus(editing.job_id, status).catch(() => {});
    refresh();
  };

  return (
    <div className="space-y-3">
      <div className="rounded-2xl bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold">Your applications</h2>
        <p className="mt-1 text-sm text-slate-500">
          Tap a status to update it once you've pressed submit on the employer's site.
        </p>
      </div>

      {!loaded ? (
        <p className="rounded-2xl bg-white p-4 text-sm text-slate-500 shadow-sm">Loading…</p>
      ) : rows.length === 0 ? (
        <p className="rounded-2xl bg-white p-4 text-sm text-slate-500 shadow-sm">
          Nothing tracked yet — approved packs land here automatically.
        </p>
      ) : (
        rows.map((row) => (
          <div
            key={row.job_id}
            className="flex items-center justify-between gap-3 rounded-2xl bg-white p-4 shadow-sm"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{row.job_title || row.job_id}</p>
              {row.company && <p className="truncate text-xs text-slate-500">{row.company}</p>}
              {row.applied_at && (
                <p className="text-xs text-slate-400">
                  Applied {new Date(row.applied_at).toLocaleDateString("en-GB")}
                </p>
              )}
            </div>
            <button
              onClick={() => setEditing(row)}
              className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold ${
                STATUS_STYLE[row.status] ?? "bg-slate-100 text-slate-600"
              }`}
            >
              {STATUS_LABELS[row.status] ?? row.status}
            </button>
          </div>
        ))
      )}

      <PlanCard />

      <Sheet
        open={editing !== null}
        title={`Update “${editing?.job_title || editing?.job_id}”`}
        onClose={() => setEditing(null)}
      >
        <div className="space-y-2">
          {Object.entries(STATUS_LABELS).map(([status, label]) => (
            <button
              key={status}
              onClick={() => void updateStatus(status)}
              aria-pressed={editing?.status === status}
              className={`w-full rounded-xl border px-4 py-3 text-left text-sm font-medium ${
                editing?.status === status
                  ? "border-brand-600 bg-brand-50 text-brand-700"
                  : "border-slate-200 text-slate-700"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </Sheet>
    </div>
  );
}
