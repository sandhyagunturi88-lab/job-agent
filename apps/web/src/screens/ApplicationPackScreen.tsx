import { useState } from "react";
import type { useRun } from "../lib/api";

export default function ApplicationPackScreen({ run }: { run: ReturnType<typeof useRun> }) {
  const packs = run.snapshot?.values.application_packs ?? [];
  const [copied, setCopied] = useState<string | null>(null);

  if (packs.length === 0) {
    return (
      <p className="rounded-2xl bg-white p-4 text-sm text-slate-600 shadow-sm">
        Application Packs appear here after you approve a tailored CV: your CV plus copy-ready
        answers, and a link to the employer's page — where <strong>you</strong> press submit.
      </p>
    );
  }

  const copy = (key: string, text: string) => {
    void navigator.clipboard.writeText(text);
    setCopied(key);
    window.setTimeout(() => setCopied((c) => (c === key ? null : c)), 1500);
  };

  return (
    <div className="space-y-3">
      {packs.map((pack) => (
        <div key={pack.job_id} className="rounded-2xl bg-white p-4 shadow-sm">
          <h3 className="font-semibold leading-snug">{pack.job_title || pack.job_id}</h3>
          {pack.company && <p className="text-sm text-slate-500">{pack.company}</p>}

          <details className="mt-3 rounded-xl border border-slate-100 p-3">
            <summary className="cursor-pointer text-sm font-medium text-slate-700">
              Tailored CV ({pack.tailored_cv.changes.length} changes)
            </summary>
            <p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">
              {pack.tailored_cv.full_text}
            </p>
            <button
              onClick={() => copy(`${pack.job_id}:cv`, pack.tailored_cv.full_text)}
              className="mt-2 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium"
            >
              {copied === `${pack.job_id}:cv` ? "Copied ✓" : "Copy CV text"}
            </button>
          </details>

          <ul className="mt-3 space-y-2">
            {pack.answers.map((answer) => {
              const key = `${pack.job_id}:${answer.field}`;
              return (
                <li key={answer.field} className="flex items-start justify-between gap-3 text-sm">
                  <div className="min-w-0">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      {answer.field.replace(/_/g, " ")}
                    </p>
                    <p className="text-slate-700">{answer.text}</p>
                  </div>
                  <button
                    onClick={() => copy(key, answer.text)}
                    className={`shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium ${
                      copied === key ? "bg-emerald-50 text-emerald-700" : "bg-slate-100"
                    }`}
                  >
                    {copied === key ? "Copied ✓" : "Copy"}
                  </button>
                </li>
              );
            })}
          </ul>

          <a
            href={pack.apply_url}
            target="_blank"
            rel="noreferrer"
            className="mt-4 block w-full rounded-xl bg-brand-600 py-3 text-center font-semibold text-white"
          >
            Open employer's application page →
          </a>
          <p className="mt-2 text-center text-xs text-slate-400">
            JobPilot never submits for you — the final click is always yours.
          </p>
        </div>
      ))}
    </div>
  );
}
