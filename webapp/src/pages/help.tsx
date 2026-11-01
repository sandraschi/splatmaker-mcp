export function Help() {
	return (
		<div data-testid="help-page" className="space-y-4">
			<h1 className="text-xl font-bold">Help</h1>

			<section className="rounded border border-zinc-800 bg-zinc-900 p-4 space-y-2">
				<h2 className="text-lg font-semibold">
					What is Nerfstudio? (What is this engine?)
				</h2>
				<p className="text-sm text-zinc-300">
					Nerfstudio is a free, open-source (Apache-2.0) framework from UC
					Berkeley for turning ordinary photos or video into 3D scenes. This
					server uses its <code>Splatfacto</code> method, which reconstructs the
					scene as a <em>Gaussian splat</em> — millions of soft 3D blobs that
					render into a photorealistic, navigable 3D world. It is the free
					alternative to paid splat services (e.g. WorldLabs Marble API): same
					photo/video in, 3D world out, zero marginal cost, everything runs on
					this machine&apos;s NVIDIA GPU.
				</p>
				<p className="text-sm text-zinc-300">
					The pipeline has three real command-line stages, all verified against
					their actual <code>--help</code> output: <code>ns-process-data</code>{" "}
					(photos/video → camera poses), <code>ns-train splatfacto</code> (poses
					→ trained splat, ~15k iterations, ~10 min on an RTX 4090),{" "}
					<code>ns-export gaussian-splat</code> (trained model →{" "}
					<code>.ply</code> file you can open in viewers or import into
					Blender/Resonite/VRChat).
				</p>
				<p className="text-sm text-zinc-300">
					One load-bearing limitation: like all FOSS splat pipelines, Nerfstudio
					emits <strong>no collision mesh</strong>. Before any VR use, route the{" "}
					<code>.ply</code> through <code>blender-mcp</code>&apos;s{" "}
					<code>blender_splatting</code> tool to generate a collider — otherwise
					the world looks right and has no floor.
				</p>
			</section>

			<section className="rounded border border-zinc-800 bg-zinc-900 p-4 space-y-2">
				<h2 className="text-lg font-semibold">Engine install & repair</h2>
				<p className="text-sm text-zinc-300">
					The engine is a Python extra (~hundreds of packages incl. PyTorch with
					CUDA). Install or repair it with:
				</p>
				<pre className="rounded bg-zinc-950 p-3 font-mono text-sm text-amber-200">
					uv sync --extra engine
				</pre>
				<p className="text-sm text-zinc-300">
					Then verify with <code>ns-train --help</code> (exit 0 = healthy).
					Known trap, fixed 2026-11-01: a plain <code>uv sync</code> (without{" "}
					<code>--extra engine</code>) silently <em>uninstalls</em> the engine
					packages again — always re-sync with the extra. If the Status page
					shows <code>verified: broken</code>, its error line names the missing
					package; installing it and restarting the backend clears it.
				</p>
			</section>

			<section className="rounded border border-zinc-800 bg-zinc-900 p-4 space-y-2">
				<h2 className="text-lg font-semibold">Workflow</h2>
				<ol className="list-decimal pl-5 text-sm text-zinc-300 space-y-1">
					<li>
						Capture: one folder of sharp, overlapping phone photos (or a slow
						walk-around video).
					</li>
					<li>Generate page: start a job, get a job id immediately.</li>
					<li>
						Jobs page: poll until status is done (real training takes minutes).
					</li>
					<li>Gallery page: fetch the .ply path for the finished job.</li>
					<li>Collide: blender-mcp blendersplatting before any VR import.</li>
				</ol>
				<p className="text-sm text-zinc-300">
					Full reference: <code>docs/TOOLS.md</code>,{" "}
					<code>docs/TROUBLESHOOTING.md</code>, <code>docs/ONBOARDING.md</code>{" "}
					in the repo.
				</p>
			</section>
		</div>
	);
}
