import type { RunSnapshot } from "../lib/api";

const STEPS = ["Found", "Pick", "CV", "Pack"] as const;

/** Which of Found → Pick → CV → Pack the run has reached (-1 = no run). */
export function runStage(snapshot: RunSnapshot | null): number {
  if (!snapshot || (snapshot.phase === null && snapshot.next_nodes.length === 0)) return -1;
  if (snapshot.phase === "done") return 4; // all complete
  if (snapshot.interrupt?.type === "pick_jobs") return 1;
  if (
    snapshot.interrupt?.type === "approve_cv" ||
    ["tailor_cv", "validate_cv", "flag_manual_edit", "pick_jobs", "learn_preferences"].includes(
      snapshot.phase ?? "",
    )
  )
    return 2;
  return 0; // retrieve / llm_rerank
}

export default function Stepper({ snapshot }: { snapshot: RunSnapshot | null }) {
  const stage = runStage(snapshot);
  if (stage < 0) return null;

  return (
    <ol aria-label="Run progress" className="mt-2 flex items-center gap-1">
      {STEPS.map((label, i) => {
        const state = i < stage ? "done" : i === stage ? "current" : "todo";
        return (
          <li key={label} className="flex flex-1 items-center gap-1">
            <span
              aria-current={state === "current" ? "step" : undefined}
              className={`flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ${
                state === "done"
                  ? "bg-emerald-50 text-emerald-700"
                  : state === "current"
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-400"
              }`}
            >
              <span aria-hidden>{state === "done" ? "✓" : "●"}</span>
              {label}
            </span>
            {i < STEPS.length - 1 && (
              <span aria-hidden className="h-px flex-1 bg-slate-200" />
            )}
          </li>
        );
      })}
    </ol>
  );
}
