import type { useRun } from "../lib/api";

export default function ApplicationPackScreen({ run }: { run: ReturnType<typeof useRun> }) {
  const packs = run.snapshot?.values.application_packs ?? [];

  if (packs.length === 0) {
    return (
      <p className="rounded-2xl bg-white p-4 text-sm text-slate-600 shadow-sm">
        Application Packs appear here after you approve a tailored CV: your CV plus
        copy-ready answers, and a link to the employer's page — where{" "}
        <strong>you</strong> press submit.
      </p>
    );
  }

  const copy = (text: string) => void navigator.clipboard.writeText(text);

  return (
    <div className="space-y-4">
      {packs.map((pack) => (
        <div key={pack.job_id} className="rounded-2xl bg-white p-4 shadow-sm">
          <h3 className="font-semibold">Pack for {pack.job_id}</h3>
          <ul className="mt-2 space-y-2">
            {pack.answers.map((answer) => (
              <li key={answer.field} className="flex items-center justify-between gap-2 text-sm">
                <div>
                  <p className="text-xs font-semibold uppercase text-slate-500">
                    {answer.field.replace(/_/g, " ")}
                  </p>
                  <p>{answer.text}</p>
                </div>
                <button
                  onClick={() => copy(answer.text)}
                  className="shrink-0 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium"
                >
                  Copy
                </button>
              </li>
            ))}
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
