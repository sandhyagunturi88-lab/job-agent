export default function OnboardingScreen() {
  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold">Welcome to JobPilot UK</h2>
      <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-600">
        <li>Upload your CV once — we build your evidenced master inventory from it.</li>
        <li>Set preferences: roles, locations, salary floor, contract types.</li>
        <li>Pick a plan (Free: 5 matches/week, 1 tailored CV · Pro: unlimited).</li>
      </ol>
      <p className="rounded-2xl bg-brand-50 p-4 text-sm text-brand-700">
        Phase 4 builds this flow (CV upload → Supabase Storage, preference form, Stripe plan
        picker). A demo profile is used until then.
      </p>
    </div>
  );
}
