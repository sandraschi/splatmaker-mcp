import { useEffect, useState } from "react";
import type { SkillSurface } from "../lib/api";
import { api } from "../lib/api";

export function Skills() {
	const [skills, setSkills] = useState<SkillSurface | null>(null);
	const [err, setErr] = useState<string | null>(null);
	useEffect(() => {
		api
			.skills()
			.then(setSkills)
			.catch((e) => setErr(String(e)));
	}, []);
	return (
		<div data-testid="skills-page" className="space-y-4">
			<h1 className="text-xl font-bold">Skills</h1>
			{err && <div className="text-sm text-red-400">{err}</div>}
			{!skills && !err && (
				<div className="text-sm text-zinc-300">Loading skill surface…</div>
			)}
			{skills && (
				<>
					<div className="rounded border border-zinc-800 bg-zinc-900 p-4">
						<div className="font-mono text-sm font-semibold">
							prompt: {skills.prompt.name}
						</div>
						<pre className="mt-2 whitespace-pre-wrap text-sm text-zinc-300">
							{skills.prompt.text}
						</pre>
					</div>
					<div className="rounded border border-zinc-800 bg-zinc-900 p-4">
						<div className="font-mono text-sm font-semibold">
							resource: {skills.resource.uri}
						</div>
						<div className="mt-1 text-sm text-zinc-300">
							{skills.resource.description} — same rows as GET /api/jobs.
						</div>
					</div>
				</>
			)}
		</div>
	);
}
