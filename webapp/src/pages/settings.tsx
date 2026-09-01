import { BackupCard } from "../components/BackupCard";

export function Settings() {
  return (
    <div data-testid="settings-page" className="space-y-6 max-w-2xl">
      <h1 className="text-xl font-bold">Settings</h1>
      <p className="text-sm text-zinc-400">Self-hosted splats — no API key. Engine 15k iters (env <code>SPLATMAKER_MAX_ITERATIONS</code>).</p>
      <BackupCard />
      <div className="rounded border border-zinc-800 bg-zinc-900 p-4 text-xs text-zinc-500">Dark mode always on. Health: <code>GET /api/health</code> · Jobs: <code>GET /api/jobs</code></div>
    </div>
  );
}
