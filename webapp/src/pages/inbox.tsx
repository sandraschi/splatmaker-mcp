import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Job } from "../lib/api";
import { api } from "../lib/api";

export function Inbox() {
	const [failed, setFailed] = useState<Job[]>([]);
	const [running, setRunning] = useState<Job[]>([]);
	const [err, setErr] = useState<string | null>(null);
	useEffect(() => {
		api
			.jobs()
			.then((r) => {
				setFailed(r.jobs.filter((j) => j.status === "failed"));
				setRunning(
					r.jobs.filter((j) => j.status === "running" || j.status === "queued"),
				);
			})
			.catch((e) => setErr(String(e)));
	}, []);
	return (
		<div data-testid="inbox-page" className="space-y-4">
			<h1 className="text-xl font-bold">Inbox</h1>
			<p className="text-sm text-zinc-300">
				Jobs that need attention: failed jobs (read the message, fix the input,
				start a new one) and jobs still in flight.
			</p>
			{err && <div className="text-sm text-red-400">{err}</div>}
			<h2 className="text-lg font-semibold">Failed ({failed.length})</h2>
			<div className="space-y-2">
				{failed.length === 0 ? (
					<div className="text-sm text-zinc-300">Nothing failed. Good.</div>
				) : (
					failed.map((j) => (
						<div
							key={j.job_id}
							data-testid={`inbox-failed-${j.job_id}`}
							className="rounded border border-red-900 bg-zinc-900 p-3"
						>
							<div className="font-mono text-sm">{j.job_id}</div>
							<div className="text-sm text-zinc-300">
								{j.kind} · {new Date(j.created_at * 1000).toLocaleString()}
							</div>
							<div className="mt-1 text-sm text-red-300">{j.message}</div>
						</div>
					))
				)}
			</div>
			<h2 className="text-lg font-semibold">In flight ({running.length})</h2>
			<div className="space-y-2">
				{running.length === 0 ? (
					<div className="text-sm text-zinc-300">
						Nothing running — start one at{" "}
						<Link to="/generate" className="text-amber-200">
							Generate
						</Link>
						.
					</div>
				) : (
					running.map((j) => (
						<div
							key={j.job_id}
							className="rounded border border-zinc-800 bg-zinc-900 p-3"
						>
							<div className="font-mono text-sm">{j.job_id}</div>
							<div className="text-sm text-zinc-300">
								{j.kind} · {j.status}
							</div>
						</div>
					))
				)}
			</div>
		</div>
	);
}
