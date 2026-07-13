import { useEffect, useState } from "react";
import { Radio, AlertTriangle } from "lucide-react";

// SCAFFOLD NOTE (Implementation Honesty Standard): this is a minimal single-page
// shell, not the full WEBAPP_SOTA_STANDARDS mandatory page set (Dashboard, Apps
// Hub, Tools Hub, Skill, LLM Chat, Status/Audit). Those are a fast-follow once
// the splat engine is actually wired - building a full Tools Hub for tools that
// honestly return not_implemented would be premature polish over a stub.

interface Health {
  status: string;
  server: string;
  version: string;
  uptime_seconds: number;
  engine_configured: boolean;
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setError("Backend unreachable on :11091 - is start.ps1 running?"));
  }, []);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-8">
      <header className="flex items-center gap-3 mb-8">
        <Radio className="text-amber-500" size={28} />
        <h1 className="text-2xl font-bold">splatmaker-mcp</h1>
        <span className="text-zinc-500 text-sm">v0.1.0 &mdash; scaffold</span>
      </header>

      {error && (
        <div className="flex items-center gap-2 bg-red-950/50 border border-red-800 rounded-lg p-4 mb-6">
          <AlertTriangle className="text-red-400" size={20} />
          <span>{error}</span>
        </div>
      )}

      {health && (
        <div className="bg-zinc-900 rounded-lg p-6 border border-zinc-800 mb-6">
          <h2 className="text-lg font-semibold mb-3">Backend health</h2>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-zinc-400">Status</dt>
            <dd>{health.status}</dd>
            <dt className="text-zinc-400">Uptime</dt>
            <dd>{health.uptime_seconds}s</dd>
            <dt className="text-zinc-400">Engine configured</dt>
            <dd className={health.engine_configured ? "text-green-400" : "text-amber-400"}>
              {health.engine_configured ? "yes" : "no \u2014 see README"}
            </dd>
          </dl>
        </div>
      )}

      <div className="bg-amber-950/30 border border-amber-800/50 rounded-lg p-4 text-sm text-amber-200">
        This webapp is a scaffold. Generate/Gallery/Jobs pages ship once a splat engine
        (Postshot / gsplat / Nerfstudio) is chosen and wired &mdash; see the repo README.
      </div>
    </div>
  );
}
