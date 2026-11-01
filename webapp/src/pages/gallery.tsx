import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Job } from "../lib/api";
import { api } from "../lib/api";

export function Gallery() {
	const [done, setDone] = useState<Job[]>([]);
	const [err, setErr] = useState<string | null>(null);
	useEffect(() => {
		api
			.jobs()
			.then((r) => setDone(r.jobs.filter((j) => j.status === "done")))
			.catch((e) => setErr(String(e)));
	}, []);
	return (
		<div data-testid="gallery-page" className="space-y-4">
			<h1 className="text-xl font-bold">Gallery</h1>
			{err && <div className="text-sm text-red-400">{err}</div>}
			{done.length === 0 ? (
				<div className="text-sm text-zinc-300">
					No finished splats yet — start one at{" "}
					<Link to="/generate" className="text-amber-200">
						Generate
					</Link>
					. Finished jobs land here with their <code>.ply</code> paths (a 3D
					viewer is future work; open the .ply in SuperSplat or import it via
					blender-mcp).
				</div>
			) : (
				<div className="grid gap-3 md:grid-cols-2">
					{done.map((j) => (
						<div
							key={j.job_id}
							data-testid={`gallery-${j.job_id}`}
							className="rounded border border-zinc-800 bg-zinc-900 p-4"
						>
							<div className="font-mono text-sm">{j.job_id}</div>
							<div className="text-sm text-zinc-300">
								{j.kind} · {new Date(j.created_at * 1000).toLocaleString()}
							</div>
							{j.asset_paths?.ply && (
								<div className="mt-1 break-all font-mono text-sm text-amber-200">
									{j.asset_paths.ply}
								</div>
							)}
							<div className="mt-1 text-sm text-zinc-300">{j.message}</div>
						</div>
					))}
				</div>
			)}
		</div>
	);
}
