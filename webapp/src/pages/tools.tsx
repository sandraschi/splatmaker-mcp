import { useEffect, useState } from "react";
import type { Capabilities } from "../lib/api";
import { api } from "../lib/api";

export function Tools() {
	const [caps, setCaps] = useState<Capabilities | null>(null);
	const [err, setErr] = useState<string | null>(null);
	useEffect(() => {
		api
			.capabilities()
			.then(setCaps)
			.catch((e) => setErr(String(e)));
	}, []);
	return (
		<div data-testid="tools-page" className="space-y-4">
			<h1 className="text-xl font-bold">Tools</h1>
			{err && <div className="text-sm text-red-400">{err}</div>}
			{!caps && !err && (
				<div className="text-sm text-zinc-300">Loading tool catalog…</div>
			)}
			{caps && (
				<>
					<div className="text-sm text-zinc-300">
						{caps.server} v{caps.version} · {caps.tools.length} MCP tools (plus{" "}
						<code>splat_workflow</code> prompt, <code>splatmaker://jobs</code>{" "}
						resource)
					</div>
					<div className="grid gap-3 md:grid-cols-2">
						{caps.tools.map((t) => (
							<div
								key={t.name}
								data-testid={`tool-${t.name}`}
								className="rounded border border-zinc-800 bg-zinc-900 p-4"
							>
								<div className="font-mono text-sm font-semibold">{t.name}</div>
								<div className="mt-1 text-sm text-zinc-300">
									{t.description}
								</div>
								{t.operations.length > 0 && (
									<div className="mt-2 flex flex-wrap gap-1">
										{t.operations.map((op) => (
											<span
												key={op}
												className="rounded bg-zinc-800 px-2 py-0.5 font-mono text-sm text-amber-200"
											>
												{op}
											</span>
										))}
									</div>
								)}
							</div>
						))}
					</div>
					<h2 className="text-lg font-bold">REST endpoints</h2>
					<div className="space-y-1">
						{caps.rest.map((r) => (
							<div key={r} className="font-mono text-sm text-zinc-300">
								{r}
							</div>
						))}
					</div>
				</>
			)}
		</div>
	);
}
