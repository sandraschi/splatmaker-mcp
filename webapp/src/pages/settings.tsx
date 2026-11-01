import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Status } from "../lib/api";
import { api } from "../lib/api";

const ENV_ROWS: [string, string][] = [
	[
		"SPLATMAKER_MAX_ITERATIONS",
		"15000 — ns-train iterations (Nerfstudio default 30000)",
	],
	[
		"SPLATMAKER_JOBS_DB",
		"~/.splatmaker-mcp/jobs.db — SQLite job store location",
	],
	[
		"SPLATMAKER_HOST / SPLATMAKER_PORT",
		"127.0.0.1 / 11091 (MCP_PORT honored as fallback)",
	],
	["SPLATMAKER_LOG_LEVEL", "info — uvicorn log level for the sidecar"],
];

export function Settings() {
	const [status, setStatus] = useState<Status | null>(null);
	const [err, setErr] = useState<string | null>(null);
	useEffect(() => {
		api
			.status()
			.then(setStatus)
			.catch((e) => setErr(String(e)));
	}, []);
	return (
		<div data-testid="settings-page" className="space-y-4">
			<h1 className="text-xl font-bold">Settings</h1>
			{err && <div className="text-sm text-red-400">{err}</div>}
			{status && (
				<div className="rounded border border-zinc-800 bg-zinc-900 p-4 space-y-1">
					<h2 className="text-lg font-semibold">Engine</h2>
					<div className="text-sm text-zinc-300">
						Nerfstudio/Splatfacto · {status.max_iterations} iterations ·
						verified: {status.engine_verified}
						{status.engine_version && ` (${status.engine_version})`}
					</div>
					{status.engine_error && (
						<div className="text-sm text-red-300">{status.engine_error}</div>
					)}
					<div className="text-sm text-zinc-300">
						No API key needed — everything runs on this machine. Repair:{" "}
						<code>uv sync --extra engine</code> (see{" "}
						<Link to="/help" className="text-amber-200">
							Help
						</Link>
						).
					</div>
				</div>
			)}
			<div className="rounded border border-zinc-800 bg-zinc-900 p-4">
				<h2 className="text-lg font-semibold">Environment</h2>
				<div className="mt-2 space-y-1">
					{ENV_ROWS.map(([k, v]) => (
						<div key={k} className="text-sm text-zinc-300">
							<code className="font-mono text-amber-200">{k}</code> — {v}
						</div>
					))}
				</div>
			</div>
		</div>
	);
}
