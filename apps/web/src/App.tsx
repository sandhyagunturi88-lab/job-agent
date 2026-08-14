import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useRun } from "./lib/api";
import ApplicationPackScreen from "./screens/ApplicationPackScreen";
import CVDiffScreen from "./screens/CVDiffScreen";
import OnboardingScreen from "./screens/OnboardingScreen";
import TodayScreen from "./screens/TodayScreen";
import TrackerScreen from "./screens/TrackerScreen";

const tabs = [
  { to: "/today", label: "Today", icon: "☀️" },
  { to: "/cv", label: "CV", icon: "📄" },
  { to: "/pack", label: "Pack", icon: "🎒" },
  { to: "/tracker", label: "Tracker", icon: "📌" },
];

export default function App() {
  const run = useRun();

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur">
        <h1 className="text-lg font-bold text-brand-700">JobPilot UK</h1>
        <p className="text-xs text-slate-500">
          {run.snapshot
            ? `Run ${run.snapshot.thread_id.split(":")[1]} — ${run.snapshot.interrupt ? "waiting for you" : (run.snapshot.phase ?? "idle")}`
            : "No run yet today"}
        </p>
      </header>

      <main className="flex-1 overflow-y-auto px-4 py-4 pb-24">
        <Routes>
          <Route path="/" element={<Navigate to="/today" replace />} />
          <Route path="/onboarding" element={<OnboardingScreen />} />
          <Route path="/today" element={<TodayScreen run={run} />} />
          <Route path="/cv" element={<CVDiffScreen run={run} />} />
          <Route path="/pack" element={<ApplicationPackScreen run={run} />} />
          <Route path="/tracker" element={<TrackerScreen run={run} />} />
        </Routes>
      </main>

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
            <span aria-hidden>{tab.icon}</span>
            {tab.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
