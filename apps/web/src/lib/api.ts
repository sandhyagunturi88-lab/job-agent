import type {
  ApplicationPack,
  CVInventoryItem,
  JobMatch,
  PreferenceProfile,
  TailoredCV,
} from "@jobpilot/schemas";
import { useCallback, useEffect, useRef, useState } from "react";

/** Slim job summary sent alongside the approve_cv interrupt. */
export interface JobSummary {
  title: string;
  company: string;
  location: string;
}

/** Snapshot of a graph run as returned by the API / WebSocket stream. */
export interface RunSnapshot {
  thread_id: string;
  phase: string | null;
  next_nodes: string[];
  interrupt:
    | { type: "pick_jobs"; matches: JobMatch[]; limited_from?: number }
    | { type: "approve_cv"; tailored_cvs: TailoredCV[]; jobs: Record<string, JobSummary> }
    | null;
  values: {
    matches?: JobMatch[];
    tailored_cvs?: TailoredCV[];
    application_packs?: ApplicationPack[];
    [key: string]: unknown;
  };
}

export interface ProfileResponse {
  profile: PreferenceProfile | null;
  plan: string;
  inventory_count: number;
  onboarded: boolean;
}

export interface ApplicationRow {
  job_id: string;
  status: string;
  job_title: string;
  company: string;
  apply_url: string;
  applied_at: string | null;
  created_at: string | null;
}

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    // surface FastAPI's {"detail": "..."} as a readable message
    let detail = body;
    try {
      detail = JSON.parse(body).detail ?? body;
    } catch {
      /* not JSON */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json();
}

const get = <T,>(path: string) => request<T>(path);
const send = <T,>(method: string, path: string, body: unknown) =>
  request<T>(path, { method, body: JSON.stringify(body) });

// --- profile / onboarding / tracker ----------------------------------------

export const getProfile = () => get<ProfileResponse>("/api/v1/me/profile");
export const saveProfile = (profile: PreferenceProfile) =>
  send<ProfileResponse>("PUT", "/api/v1/me/profile", profile);
export const savePlan = (plan: "free" | "pro") =>
  send<{ plan: string }>("PUT", "/api/v1/me/plan", { plan });
export const uploadCv = (cv_text: string) =>
  send<{ inventory: CVInventoryItem[]; counts: Record<string, number> }>(
    "POST",
    "/api/v1/me/cv",
    { cv_text },
  );
export const getInventory = () => get<CVInventoryItem[]>("/api/v1/me/inventory");
export const getApplications = () => get<ApplicationRow[]>("/api/v1/me/applications");
export const setApplicationStatus = (jobId: string, status: string) =>
  send<{ job_id: string; status: string }>("PUT", `/api/v1/me/applications/${jobId}`, { status });

// --- CV Builder plugin (apps/cv-builder — separate service, own origin) -----

export const cvBuilderUrl: string =
  import.meta.env.VITE_CVBUILDER_URL ?? "http://localhost:3000";

/** Extract raw text from a PDF/DOCX/TXT CV via the CV Builder plugin
 *  (deterministic — the file is parsed in memory and never stored). */
export async function extractCvFile(file: File): Promise<string> {
  const fd = new FormData();
  fd.append("file", file);
  let res: Response;
  try {
    res = await fetch(`${cvBuilderUrl}/api/extract-text`, { method: "POST", body: fd });
  } catch {
    throw new Error(
      "Couldn't reach the CV Builder service for PDF/Word import — start it with " +
        "`npm run dev:cv-builder`, or paste your CV as text instead.",
    );
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}) as { error?: string });
    throw new Error(body.error ?? "Could not read that file — paste your CV as text instead.");
  }
  return (await res.json()).text;
}

// --- billing ----------------------------------------------------------------

export interface BillingStatus {
  plan: string;
  pro_price: string;
  week: string;
  limits: { matches: number; cvs: number } | null; // null = unlimited (pro)
  used: { matches: number; cvs: number };
  dev_billing: boolean;
}

export const getBilling = () => get<BillingStatus>("/api/v1/billing");
export const startCheckout = () =>
  send<{ url: string | null }>("POST", "/api/v1/billing/checkout", {});
export const startPortal = () =>
  send<{ url: string | null }>("POST", "/api/v1/billing/portal", {});
export const devUpgrade = () => send<{ plan: string }>("POST", "/api/v1/billing/dev-upgrade", {});
export const devDowngrade = () =>
  send<{ plan: string }>("POST", "/api/v1/billing/dev-downgrade", {});

/** Loads the user's profile once; `refresh` after onboarding writes. */
export function useProfile() {
  const [data, setData] = useState<ProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setData(await getProfile());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { data, loading, refresh };
}

// --- run lifecycle ----------------------------------------------------------

const runExists = (snap: RunSnapshot) => snap.phase !== null || snap.next_nodes.length > 0;

/**
 * Drives one daily graph run: reattaches to today's run on load, starts a new
 * one on demand (idempotent per day), subscribes to live state over WebSocket,
 * and answers interrupts via /resume.
 */
export function useRun() {
  const [snapshot, setSnapshot] = useState<RunSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const subscribe = useCallback((threadId: string) => {
    wsRef.current?.close();
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws/runs/${threadId}`);
    ws.onmessage = (event) => setSnapshot(JSON.parse(event.data));
    wsRef.current = ws;
  }, []);

  // Reattach to today's run (e.g. the overnight cron already ran it, or the
  // user closed the app mid-interrupt — checkpointer state survives).
  useEffect(() => {
    let cancelled = false;
    void get<RunSnapshot>("/api/v1/runs/today")
      .then((snap) => {
        if (cancelled || !runExists(snap)) return;
        setSnapshot(snap);
        subscribe(snap.thread_id);
      })
      .catch(() => {})
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, [subscribe]);

  const start = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const snap = await send<RunSnapshot>("POST", "/api/v1/runs/start", {});
      setSnapshot(snap);
      subscribe(snap.thread_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, [subscribe]);

  const resume = useCallback(
    async (value: Record<string, unknown>) => {
      if (!snapshot) return;
      setBusy(true);
      setError(null);
      try {
        setSnapshot(
          await send<RunSnapshot>("POST", `/api/v1/runs/${snapshot.thread_id}/resume`, { value }),
        );
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [snapshot],
  );

  return { snapshot, loading, busy, error, start, resume };
}
