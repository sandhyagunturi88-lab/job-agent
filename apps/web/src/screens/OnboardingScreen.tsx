import type { ContractType, CVInventoryItem, PreferenceProfile } from "@jobpilot/schemas";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { cvBuilderUrl, extractCvFile, savePlan, saveProfile, uploadCv } from "../lib/api";

const CONTRACT_OPTIONS: { value: ContractType; label: string }[] = [
  { value: "permanent", label: "Permanent" },
  { value: "contract", label: "Contract" },
  { value: "temporary", label: "Temporary" },
  { value: "part_time", label: "Part-time" },
];

const KIND_LABELS: Record<string, string> = {
  role: "roles",
  achievement: "achievements",
  skill: "skills",
  education: "education",
  certification: "certifications",
};

const splitCsv = (s: string) =>
  s
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);

function StepDots({ step }: { step: number }) {
  return (
    <div className="flex justify-center gap-2" aria-label={`Step ${step} of 3`}>
      {[1, 2, 3].map((i) => (
        <span
          key={i}
          aria-hidden
          className={`h-2 rounded-full ${i === step ? "w-6 bg-brand-600" : "w-2 bg-slate-300"}`}
        />
      ))}
    </div>
  );
}

export default function OnboardingScreen({ onDone }: { onDone: () => void }) {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // step 1 — CV
  const [cvText, setCvText] = useState("");
  const [inventory, setInventory] = useState<CVInventoryItem[] | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});

  // step 2 — preferences
  const [titles, setTitles] = useState("");
  const [locations, setLocations] = useState("");
  const [minSalary, setMinSalary] = useState("");
  const [contracts, setContracts] = useState<Set<ContractType>>(new Set(["permanent"]));
  const [avoid, setAvoid] = useState("");

  const readFile = async (file: File) => {
    setError(null);
    const name = file.name.toLowerCase();
    if (name.endsWith(".pdf") || name.endsWith(".docx")) {
      // PDF/Word go through the CV Builder plugin's deterministic extractor
      setBusy(true);
      try {
        setCvText(await extractCvFile(file));
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setCvText(String(reader.result ?? ""));
    reader.readAsText(file);
  };

  const parseCv = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await uploadCv(cvText);
      setInventory(res.inventory);
      setCounts(res.counts);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const savePreferences = async () => {
    setBusy(true);
    setError(null);
    try {
      const profile: PreferenceProfile = {
        desired_titles: splitCsv(titles),
        locations: splitCsv(locations),
        min_salary: minSalary ? Number(minSalary) : null,
        contract_types: [...contracts],
        avoid_keywords: splitCsv(avoid),
        notes: [],
      };
      await saveProfile(profile);
      setStep(3);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const finish = async () => {
    setBusy(true);
    try {
      await savePlan("free");
    } catch {
      // plan defaults to free server-side anyway
    } finally {
      setBusy(false);
    }
    onDone();
    navigate("/today");
  };

  return (
    <div className="space-y-4 py-2">
      <StepDots step={step} />
      {error && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {step === 1 && (
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <h2 className="text-base font-semibold">Your CV, once</h2>
          <p className="mt-1 text-sm text-slate-500">
            We turn it into an evidence inventory — the only material ever used to tailor your
            CV. Nothing gets invented on your behalf.
          </p>

          {!inventory ? (
            <>
              <textarea
                value={cvText}
                onChange={(e) => setCvText(e.target.value)}
                rows={8}
                className="mt-3 w-full rounded-xl border border-slate-300 p-3 text-sm"
                placeholder={"Paste your CV text here…\n\nSkills\nPython, FastAPI, PostgreSQL\n\nExperience\nSenior Engineer — Acme, 2021–present\n- Cut API latency 40%"}
              />
              <label className="mt-2 block text-sm text-slate-500">
                …or upload your CV (PDF, Word, or text)
                <input
                  type="file"
                  accept=".pdf,.docx,.txt,.md,text/plain,text/markdown"
                  onChange={(e) => e.target.files?.[0] && void readFile(e.target.files[0])}
                  className="mt-1 block w-full text-xs"
                />
              </label>
              <p className="mt-1 text-xs text-slate-400">
                PDF and Word files are read by the CV Builder plugin — parsed in memory,
                never stored.
              </p>
              <button
                onClick={() => void parseCv()}
                disabled={busy || cvText.trim().length < 40}
                className="mt-4 w-full rounded-xl bg-brand-600 py-3 font-semibold text-white disabled:opacity-50"
              >
                {busy ? "Reading your CV…" : "Build my evidence inventory"}
              </button>

              <div className="mt-4 rounded-xl bg-slate-50 p-3 text-center">
                <p className="text-sm text-slate-600">Don't have a CV yet?</p>
                <a
                  href={cvBuilderUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 block w-full rounded-xl bg-slate-200 py-2.5 text-sm font-semibold text-slate-700"
                >
                  Create one in CV Studio →
                </a>
                <p className="mt-2 text-xs text-slate-400">
                  Guided steps with live preview and PDF/Word export — then come back and
                  upload it here.
                </p>
              </div>
            </>
          ) : (
            <>
              <p className="mt-3 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">
                Found {inventory.length} evidenced facts:{" "}
                {Object.entries(counts)
                  .map(([k, v]) => `${v} ${KIND_LABELS[k] ?? k}`)
                  .join(", ")}
                .
              </p>
              <ul className="mt-3 max-h-48 space-y-1 overflow-y-auto">
                {inventory.slice(0, 12).map((item) => (
                  <li key={item.id} className="text-xs text-slate-600">
                    <span className="mr-1 rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px]">
                      {item.kind}
                    </span>
                    {item.text}
                  </li>
                ))}
                {inventory.length > 12 && (
                  <li className="text-xs text-slate-400">…and {inventory.length - 12} more</li>
                )}
              </ul>
              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => setInventory(null)}
                  className="rounded-xl bg-slate-100 px-4 py-3 text-sm font-medium"
                >
                  Re-paste
                </button>
                <button
                  onClick={() => setStep(2)}
                  className="flex-1 rounded-xl bg-brand-600 py-3 font-semibold text-white"
                >
                  Looks right — continue
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {step === 2 && (
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <h2 className="text-base font-semibold">What are you looking for?</h2>
          <div className="mt-3 space-y-3 text-sm">
            <label className="block text-slate-600">
              Job titles (comma-separated)
              <input
                value={titles}
                onChange={(e) => setTitles(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                placeholder="Senior Python Engineer, Backend Engineer"
              />
            </label>
            <label className="block text-slate-600">
              Locations
              <input
                value={locations}
                onChange={(e) => setLocations(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                placeholder="London, Remote"
              />
            </label>
            <label className="block text-slate-600">
              Minimum salary (£/year)
              <input
                type="number"
                inputMode="numeric"
                value={minSalary}
                onChange={(e) => setMinSalary(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                placeholder="70000"
              />
            </label>
            <fieldset>
              <legend className="text-slate-600">Contract types</legend>
              <div className="mt-1 flex flex-wrap gap-2">
                {CONTRACT_OPTIONS.map((opt) => {
                  const on = contracts.has(opt.value);
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      aria-pressed={on}
                      onClick={() => {
                        const next = new Set(contracts);
                        on ? next.delete(opt.value) : next.add(opt.value);
                        setContracts(next);
                      }}
                      className={`rounded-full border px-3 py-1.5 ${
                        on
                          ? "border-brand-600 bg-brand-50 text-brand-700"
                          : "border-slate-200 text-slate-600"
                      }`}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </fieldset>
            <label className="block text-slate-600">
              Avoid (keywords, optional)
              <input
                value={avoid}
                onChange={(e) => setAvoid(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
                placeholder="php, on-site, agencies"
              />
            </label>
          </div>
          <button
            onClick={() => void savePreferences()}
            disabled={busy || splitCsv(titles).length === 0}
            className="mt-4 w-full rounded-xl bg-brand-600 py-3 font-semibold text-white disabled:opacity-50"
          >
            {busy ? "Saving…" : "Save preferences"}
          </button>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-3">
          <div className="rounded-2xl border-2 border-brand-600 bg-white p-5 shadow-sm">
            <div className="flex items-baseline justify-between">
              <h2 className="text-base font-semibold">Free</h2>
              <span className="text-sm font-semibold text-slate-700">£0</span>
            </div>
            <ul className="mt-2 space-y-1 text-sm text-slate-600">
              <li>· 5 matches per week</li>
              <li>· 1 tailored CV per week</li>
              <li>· Application Pack + tracker</li>
            </ul>
          </div>
          <div className="rounded-2xl bg-white p-5 shadow-sm">
            <div className="flex items-baseline justify-between">
              <h2 className="text-base font-semibold">Pro</h2>
              <span className="text-sm font-semibold text-slate-700">£9/month</span>
            </div>
            <ul className="mt-2 space-y-1 text-sm text-slate-600">
              <li>· Unlimited matches and tailored CVs</li>
              <li>· Cancel anytime, keep everything generated</li>
            </ul>
            <p className="mt-2 text-xs text-slate-400">
              Start on Free — you can upgrade any time from the Tracker tab. No card needed
              today, no trial countdown.
            </p>
          </div>
          <button
            onClick={() => void finish()}
            disabled={busy}
            className="w-full rounded-xl bg-brand-600 py-3 font-semibold text-white disabled:opacity-50"
          >
            Start with Free
          </button>
        </div>
      )}
    </div>
  );
}
