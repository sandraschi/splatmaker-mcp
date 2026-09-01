import { useEffect, useState } from "react";
import { api, Job } from "../lib/api";

export function Jobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const load = () => api.jobs().then((r) => setJobs(r.jobs)).catch((e) => setErr(String(e)));
  useEffect(() => { load(); const id = setInterval(load, 5000); return () => clearInterval(id); }, []);
  return (
    <div data-testid="jobs-page" className="space-y-4">
      <h1 className="text-xl font-bold">Jobs</h1>
      <div data-testid="jobs-list" className="space-y-2">
        {jobs.length === 0 ? <div className="text-sm text-zinc-500">No jobs yet — start one at Generate.</div> : jobs.map((j) => (
          <div key={j.job_id} data-testid={`job-${j.job_id}`} className="rounded border border-zinc-800 bg-zinc-900 p-3">
            <div className="text-sm font-mono">{j.job_id}</div>
            <div className="text-xs text-zinc-400">{j.kind} · {j.status} · {new Date(j.created_at*1000).toLocaleString()}</div>
            <div className="text-xs text-zinc-300 mt-1">{j.message}</div>
          </div>
        ))}
      </div>
      {err && <div className="text-xs text-red-400">{err}</div>}
      <div className="text-xs text-zinc-500">Persisted in SQLite — survives restart. Polls every 5s.</div>
    </div>
  );
}
