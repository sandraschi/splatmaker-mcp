import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/api";

export function Logs() {
	const [logs, setLogs] = useState<string[]>([]);
	const [err, setErr] = useState<string | null>(null);
	const load = useCallback(
		() =>
			api
				.logs(200)
				.then((r) => {
					setLogs(r.logs);
					setErr(null);
				})
				.catch((e) => setErr(String(e))),
		[],
	);
	useEffect(() => {
		load();
		const id = setInterval(load, 5000);
		return () => clearInterval(id);
	}, [load]);
	return (
		<div data-testid="logs-page" className="space-y-4">
			<div className="flex items-center gap-3">
				<h1 className="text-xl font-bold">Logs</h1>
				<button
					type="button"
					data-testid="logs-refresh"
					onClick={load}
					className="rounded border border-zinc-700 px-3 py-1 text-sm"
				>
					Refresh
				</button>
			</div>
			{err && <div className="text-sm text-red-400">{err}</div>}
			<pre
				data-testid="logs-list"
				className="max-h-[60vh] overflow-auto rounded border border-zinc-800 bg-zinc-950 p-3 font-mono text-sm text-zinc-300"
			>
				{logs.length === 0 ? "No log lines yet." : logs.join("\n")}
			</pre>
			<div className="text-sm text-zinc-300">
				In-memory ring (last 500 lines), polls every 5s.
			</div>
		</div>
	);
}
