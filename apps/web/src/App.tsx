import { Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";
import Stepper from "./components/Stepper";
import { useProfile, useRun } from "./lib/api";
import ApplicationPackScreen from "./screens/ApplicationPackScreen";
import CVDiffScreen from "./screens/CVDiffScreen";
import JobDetailScreen from "./screens/JobDetailScreen";
import OnboardingScreen from "./screens/OnboardingScreen";
import TodayScreen from "./screens/TodayScreen";
import TrackerScreen from "./screens/TrackerScreen";

const ICONS: Record<string, string> = {
  // simple single-path icons keep the tab bar calm and licence-free
  today:
    "M12 3v2m0 14v2M3 12h2m14 0h2M5.6 5.6l1.4 1.4m9.9 9.9 1.4 1.4M5.6 18.4 7 17m9.9-9.9 1.5-1.5M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z",
  cv: "M7 3h7l5 5v13H7V3Zm7 0v5h5M10 12h6m-6 4h6",
  pack: "M4 8h16v12H4V8Zm4 0V6a4 4 0 0 1 8 0v2",
  tracker: "M5 6h2m3 0h9M5 12h2m3 0h9M5 18h2m3 0h9",
};

const tabs = [
  { to: "/today", label: "Today", icon: "today" },
  { to: "/cv", label: "CV", icon: "cv" },
  { to: "/pack", label: "Pack", icon: "pack" },
  { to: "/tracker", label: "Tracker", icon: "tracker" },
];

const dateLabel = new Date().toLocaleDateString("en-GB", {
  weekday: "short",
  day: "numeric",
  month: "short",
});

export default function App() {
  const run = useRun();
  const profile = useProfile();
  const location = useLocation();
  const onboarding = location.pathname === "/onboarding";

  // First visit → onboarding (CV + preferences) before anything else.
  if (!profile.loading && profile.data && !profile.data.onboarded && !onboarding) {
    return <Navigate to="/onboarding" replace />;
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur">
        <div className="flex items-baseline justify-between">
          <h1 className="text-lg font-bold text-brand-700">JobPilot UK</h1>
          <span className="text-xs font-medium text-slate-500">{dateLabel}</span>
        </div>
        {!onboarding && <Stepper snapshot={run.snapshot} />}
      </header>

      <main className="flex-1 overflow-y-auto px-4 py-4 pb-28">
        <Routes>
          <Route path="/" element={<Navigate to="/today" replace />} />
          <Route
            path="/onboarding"
            element={<OnboardingScreen onDone={() => void profile.refresh()} />}
          />
          <Route path="/today" element={<TodayScreen run={run} />} />
          <Route path="/today/:jobId" element={<JobDetailScreen run={run} />} />
          <Route path="/cv" element={<CVDiffScreen run={run} />} />
          <Route path="/pack" element={<ApplicationPackScreen run={run} />} />
          <Route path="/tracker" element={<TrackerScreen run={run} />} />
        </Routes>
      </main>

      {!onboarding && (
        <nav
          aria-label="Main"
          className="fixed inset-x-0 bottom-0 z-10 mx-auto flex max-w-md border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)]"
        >
          {tabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              className={({ isActive }) =>
                `flex flex-1 flex-col items-center gap-0.5 py-2 text-xs ${
                  isActive ? "font-semibold text-brand-600" : "text-slate-500"
                }`
              }
            >
              <svg
                viewBox="0 0 24 24"
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden
              >
                <path d={ICONS[tab.icon]} />
              </svg>
              {tab.label}
            </NavLink>
          ))}
        </nav>
      )}
    </div>
  );
}
