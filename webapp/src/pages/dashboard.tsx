import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Cpu } from "lucide-react";
import { api } from "../lib/api";
import { useAppStore } from "../lib/store";

export function Dashboard() {
  const { health, checkHealth } = useAppStore();
  const [jobs, setJobs] = useState<number>(0);
  useEffect(() => {
    checkHealth();
    api.jobs().then((r) => setJobs(r.jobs.length)).catch(() => null);
  }, [checkHealth]);
  return (
    <div data-testid="dashboard" className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <div className="grid gap-4 md:grid-cols-3">
        <div data-testid="kpi-health" className="rounded border border-zinc-800 bg-zinc-900 p-4">
          <div className="text-sm text-zinc-300">Backend</div>
          <div className="text-lg font-semibold" data-testid="backend-dot">{health ? health.status : "…"}</div>
          <div className="text-sm text-zinc-300">{health ? `${health.uptime_seconds}s up · ${health.engine_configured ? "engine ready" : "engine not configured (uv sync --extra engine)"}` : "connecting to backend"}</div>
        </div>
        <div data-testid="kpi-engine" className="rounded border border-zinc-800 bg-zinc-900 p-4">
          <div className="text-sm text-zinc-300">Engine</div>
          <div className="text-lg font-semibold flex items-center gap-2"><Cpu size={16} /> Nerfstudio</div>
          <div className="text-sm text-zinc-300">splatfacto · ~15k iters · ~10 min on 4090</div>
        </div>
        <div data-testid="kpi-jobs" className="rounded border border-zinc-800 bg-zinc-900 p-4">
          <div className="text-sm text-zinc-300">Jobs</div>
          <div className="text-lg font-semibold" data-testid="jobs-count">{jobs} persisted</div>
          <div className="text-sm text-zinc-300">SQLite at ~/.splatmaker-mcp/jobs.db</div>
        </div>
      </div>
      <div className="flex gap-3">
        <Link data-testid="cta-generate" to="/generate" className="rounded bg-amber-600 px-4 py-2 text-sm font-semibold text-white">Generate from video</Link>
        <Link data-testid="cta-jobs" to="/jobs" className="rounded border border-zinc-700 px-4 py-2 text-sm">View jobs</Link>
      </div>
      <div className="rounded border border-amber-800/50 bg-amber-950/20 p-4 text-sm text-amber-200">
        Zero marginal cost — local 4090. Multi-dir images now auto-staged. Compare to Platform 1500cr/gen.
      </div>
    </div>
  );
}
