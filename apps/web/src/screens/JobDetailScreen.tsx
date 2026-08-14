import type { JobMatch } from "@jobpilot/schemas";
import { Link, useParams } from "react-router-dom";
import ScoreRing from "../components/ScoreRing";
import type { useRun } from "../lib/api";

const fmtSalary = (min?: number | null, max?: number | null) => {
  if (!min && !max) return "Not stated";
  const f = (n: number) => `£${n.toLocaleString("en-GB")}`;
  if (min && max && min !== max) return `${f(min)} – ${f(max)}`;
  return f(min ?? max ?? 0);
};

export default function JobDetailScreen({ run }: { run: ReturnType<typeof useRun> }) {
  const { jobId } = useParams();
  const snapshot = run.snapshot;
  const matches: JobMatch[] =
    snapshot?.interrupt?.type === "pick_jobs"
      ? snapshot.interrupt.matches
      : (snapshot?.values.matches ?? []);
  const match = matches.find((m) => m.job.id === jobId);

  if (!match) {
    return (
      <div className="space-y-3">
        <p className="rounded-2xl bg-white p-4 text-sm text-slate-600 shadow-sm">
          Job not found in today's run.
        </p>
        <Link to="/today" className="text-sm font-medium text-brand-600">
          ← Back to today's matches
        </Link>
      </div>
    );
  }

  const { job } = match;
  const facts: [string, string][] = [
    ["Salary", fmtSalary(job.salary_min, job.salary_max)],
    ["Contract", job.contract_type?.replace("_", " ") ?? "Not stated"],
    [
      "IR35",
      job.ir35_flag === null || job.ir35_flag === undefined
        ? "Unknown"
        : job.ir35_flag
          ? "Inside"
          : "Outside",
    ],
    ["Source", job.source.replace(/_/g, " ")],
    ["Posted", new Date(job.posted_at).toLocaleDateString("en-GB")],
  ];

  return (
    <div className="space-y-3">
      <Link to="/today" className="text-sm font-medium text-brand-600">
        ← Today's matches
      </Link>

      <div className="rounded-2xl bg-white p-5 shadow-sm">
        <div className="flex items-start gap-3">
          <ScoreRing score={match.score} />
          <div>
            <h2 className="text-base font-semibold leading-snug">{job.title}</h2>
            <p className="text-sm text-slate-500">
              {job.company} · {job.location}
            </p>
          </div>
        </div>
        {match.verdict && <p className="mt-3 text-sm text-slate-600">“{match.verdict}”</p>}

        <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2">
          {facts.map(([label, value]) => (
            <div key={label}>
              <dt className="text-xs uppercase tracking-wide text-slate-400">{label}</dt>
              <dd className="text-sm text-slate-700">{value}</dd>
            </div>
          ))}
        </dl>
      </div>

      {(match.matched_skills.length > 0 || match.gaps.length > 0) && (
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold">Your fit</h3>
          <div className="mt-2 space-y-1.5">
            {match.matched_skills.map((s) => (
              <p key={s} className="text-sm text-emerald-700">
                ✓ {s} — evidenced in your CV
              </p>
            ))}
            {match.gaps.map((g) => (
              <p key={g} className="text-sm text-amber-700">
                △ {g} — not evidenced; a gap to address
              </p>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-2xl bg-white p-5 shadow-sm">
        <h3 className="text-sm font-semibold">Job description</h3>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-600">
          {job.jd_text}
        </p>
        <a
          href={job.url}
          target="_blank"
          rel="noreferrer"
          className="mt-4 block text-sm font-medium text-brand-600"
        >
          View original posting →
        </a>
      </div>
    </div>
  );
}
