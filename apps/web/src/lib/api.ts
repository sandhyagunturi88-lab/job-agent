import type { ApplicationPack, JobMatch, TailoredCV } from "@jobpilot/schemas";
import { useCallback, useEffect, useRef, useState } from "react";

/** Snapshot of a graph run as returned by the API / WebSocket stream. */
export interface RunSnapshot {
  thread_id: string;
  phase: string | null;
  next_nodes: string[];
  interrupt:
    | { type: "pick_jobs"; matches: JobMatch[] }
    | { type: "approve_cv"; tailored_cvs: TailoredCV[] }
    | null;
  values: {
    matches?: JobMatch[];
    tailored_cvs?: TailoredCV[];
    application_packs?: ApplicationPack[];
    [key: string]: unknown;
  };
}

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

/**
 * Drives one daily graph run: starts it (idempotent per day), subscribes to
 * live state over WebSocket, and answers interrupts via /resume.
 */
export function useRun() {
  const [snapshot, setSnapshot] = useState<RunSnapshot | null>(null);
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

  useEffect(() => () => wsRef.current?.close(), []);

  const start = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const snap = await post<RunSnapshot>("/api/v1/runs/start", {});
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
        setSnapshot(await post<RunSnapshot>(`/api/v1/runs/${snapshot.thread_id}/resume`, { value }));
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [snapshot],
  );

  return { snapshot, busy, error, start, resume };
}
