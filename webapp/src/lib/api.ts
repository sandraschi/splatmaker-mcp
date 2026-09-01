export const API_BASE = "http://127.0.0.1:11091";

export interface Health {
  status: string;
  server: string;
  version: string;
  uptime_seconds: number;
  engine_configured: boolean;
}

export interface Job {
  job_id: string;
  kind: "from_video" | "from_images";
  status: "queued" | "running" | "done" | "failed";
  created_at: number;
  message: string;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => get<Health>("/api/health"),
  jobs: () => get<{ jobs: Job[] }>("/api/jobs"),
  jobStatus: (id: string) => post<{ job_id: string; status: string; message?: string }>("/api/jobs/status", { job_id: id }),
};
