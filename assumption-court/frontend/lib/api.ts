import type { CachedCase, TrialJob } from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000").replace(/\/$/, "");

async function errorText(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return typeof body.detail === "string" ? body.detail : `HTTP ${res.status}`;
  } catch {
    return `HTTP ${res.status}`;
  }
}

export async function startTrial(text: string): Promise<string> {
  const res = await fetch(`${API_BASE}/trial`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(await errorText(res));
  return (await res.json()).job_id as string;
}

export async function getTrial(jobId: string): Promise<TrialJob> {
  const res = await fetch(`${API_BASE}/trial/${jobId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(await errorText(res));
  return res.json();
}

/** Cached examples: backend first, then the static copies in /public/examples (works with the backend down). */
export async function loadExamples(): Promise<CachedCase[]> {
  try {
    const res = await fetch(`${API_BASE}/examples`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      const cases = (await res.json()) as CachedCase[];
      if (cases.length) return cases;
    }
  } catch {
    // backend unreachable: fall through to static copies
  }
  const index = (await (await fetch("/examples/index.json")).json()) as { file: string }[];
  return Promise.all(index.map(async (e) => (await fetch(`/examples/${e.file}`)).json() as Promise<CachedCase>));
}
