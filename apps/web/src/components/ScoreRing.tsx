/** Fit-score ring, coloured by bucket: strong ≥75, fair 50–74, stretch <50. */

export const scoreBucket = (score: number) =>
  score >= 75 ? "strong" : score >= 50 ? "fair" : "stretch";

const BUCKET_TEXT = {
  strong: "text-emerald-600",
  fair: "text-amber-500",
  stretch: "text-slate-400",
} as const;

export default function ScoreRing({ score }: { score: number }) {
  const r = 17;
  const c = 2 * Math.PI * r;
  return (
    <svg
      viewBox="0 0 42 42"
      className="h-11 w-11 shrink-0"
      role="img"
      aria-label={`Fit score ${score} out of 100`}
    >
      <circle cx="21" cy="21" r={r} fill="none" strokeWidth="4" className="stroke-slate-100" />
      <circle
        cx="21"
        cy="21"
        r={r}
        fill="none"
        strokeWidth="4"
        strokeLinecap="round"
        stroke="currentColor"
        strokeDasharray={c}
        strokeDashoffset={c * (1 - score / 100)}
        transform="rotate(-90 21 21)"
        className={BUCKET_TEXT[scoreBucket(score)]}
      />
      <text
        x="21"
        y="21"
        textAnchor="middle"
        dominantBaseline="central"
        className="fill-slate-700 text-[13px] font-bold"
      >
        {score}
      </text>
    </svg>
  );
}
