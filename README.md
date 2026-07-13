# splatmaker-mcp

**Self-hosted, zero-marginal-cost Gaussian-splat generation.** The FOSS alternative to worldlabs-mcp's Marble API — point it at a video or a set of images, get a navigable 3D Gaussian-splat world back, run entirely on local hardware (RTX 4090).

**Status: scaffold, v0.1.0.** Server shell, tool schemas, job tracking, fleet health/registration contract, and webapp skeleton are real and working. **The splat-generation engine itself is not yet wired** — see "Engine status" below. This is deliberate (Implementation Honesty Standard), not an oversight: the tools exist and respond honestly with `not_implemented` rather than faking success.

## Why this exists

worldlabs-mcp (Marble API) isn't cheap. This fleet has an RTX 4090 sitting idle for exactly this kind of workload. A FOSS Gaussian-splat pipeline (Postshot / gsplat / Nerfstudio-class tooling — none chosen yet) wrapped as an MCP server gets the same "photo/video → navigable 3D world" capability at zero marginal cost, feeding the same downstream chain (`blender-mcp` → `resonite-mcp` / Resonite, VRChat) that worldlabs-mcp already feeds.

There's also a plausible case this is useful beyond this fleet — the Resonite and VRChat world-building communities currently either pay for splat SaaS or fight research-grade CLI tooling directly. If this ships clean, it may be worth public release per `FLEET_PROMOTION.md`.

## Engine status

Researched 2026-07-13 (stars/age/CLI quality/speed/collider-mesh support/known bugs — sources: PyPI, GitHub, radiancefields.com, thefuture3d.com, polyvia3d.com benchmark, docs.nerf.studio). **None chosen for implementation yet** — this is a comparison to inform the choice, not a decision.

| | gsplat | Nerfstudio | Postshot |
|---|---|---|---|
| Type | CUDA rasterization library (PyTorch) | Full training/export framework (uses gsplat backend) | Proprietary desktop app (Jawset) |
| Age | Oct 2023 | Oct 2022 | Beta Dec 2023 |
| Stars / forks | ~5.3k / 897 | ~11.8k / 1.6k | N/A — closed source |
| License | Apache-2.0 | Apache-2.0 | Proprietary. **CORRECTED 2026-07-13:** earlier "verified live: all tiers €0.00" claim in this doc was WRONG — jawset.com's pricing page uses a JS-driven calculator (monthly/yearly toggle, currency selector, license-count stepper); the automated fetch used to "verify" it doesn't execute JS and was reading a pre-hydration placeholder state (identical €0.00 across three separate fetches was the tell, in hindsight). Sandra's actual browser shows Studio at roughly £40/month — trust that over anything this doc claimed about live pricing. What IS reliable: the static feature-bullet list shows "Command-line interface" listed ONLY under Studio, not Free or Indie — CLI access is Studio-exclusive, paid, not a free-tier-with-GUI-restriction-lifted situation. Single-maintainer sole proprietorship (Jascha Wetzel, Munich, Germany) regardless of price |
| Language | Python + CUDA | Python + CUDA (via gsplat) | Not published, native Windows app |
| CLI | None — write your own training script | Real CLI: `ns-process-data`, `ns-train`, `ns-export`, `ns-render` | GUI-first; CLI historically gated to paid Studio tier |
| **Collider mesh sidecar** | **No** — pure rasterizer | **Partial** — `ns-export tsdf`/`poisson`, separate command, untested against Splatfacto specifically | **No, confirmed via direct `postshot-cli.exe --help`/`export` testing 2026-07-13** — only output option is `--export-splat` (PLY/SPZ), no mesh flag exists at all |
| Speed (RTX 4090) | ~8 min (fastest) | ~10 min | ~30 min (different benchmark scale) |
| VRAM | ~4GB | ~6GB | Not specified |
| Quality (PSNR, same benchmark) | 28.1 dB | 27.9 dB | Not benchmarked head-to-head |
| Known gaps | JIT CUDA compile breaks on some PyTorch/CUDA combos; zero pipeline, all DIY glue | No fisheye/equirectangular/orthographic camera support (perspective only) — check against actual capture method | PLY exports have been reported missing attributes (normals, opacity, scale, rotation, SH coefficients) needed by some downstream tools (SOGS) |

**Working recommendation (not yet implemented):** Nerfstudio — real CLI suited to subprocess wrapping, fully Python (fits fleet's `uv`-first philosophy, zero extra glue vs. gsplat), PSNR gap vs. alternatives is within "barely perceptible" range per every source checked. **Strengthened by the pricing correction above:** Postshot's CLI isn't free either, on top of being GUI-first-designed and historically paywalled — there's no remaining cost or capability argument for it over a genuinely free, Apache-2.0, CLI-native alternative for the unattended-automation use case this server actually needs.

**Risk framing, revised again 2026-07-13 (pricing correction supersedes the free-tier framing below):** the "install Studio, hope for the best" discussion below was conducted under the mistaken belief that Studio (and its CLI) was genuinely free. It is very likely NOT — Studio appears to be a real paid tier (~£40/month per direct browser observation), gating CLI access specifically. The "frozen vs. actively churning" business-stability discussion below still stands as reasoning, but the practical upshot changes: this isn't a zero-cost hedge anymore, it's a real ~£480/year recurring cost question against a ~€100/month total AI-tools budget, competing directly with everything else in that budget. Re-evaluate before subscribing to anything — don't let the sunk research cost here push toward a subscription that wasn't actually free after all.

**Risk framing, revised 2026-07-13 (Sandra pushback, worth keeping both sides):** the "agentic-transition instability" read above assumed Postshot v1 is being actively (if distractedly) touched. The more parsimonious read: v1 is frozen in place — attention (and any v2/rebrand) has moved elsewhere, and the free-tier reset reflects "not worth maintaining a paywall we're not really selling anymore," not ongoing churn. Under that reading the risk profile inverts: a genuinely abandoned tool can't drift under you (nobody's touching it), so it's actually MORE stable day-to-day than a tool under active development. The real remaining risks are narrower: (1) today's known bugs (e.g. the PLY/SOGS attribute gap above) are permanent, never getting fixed — test against them up front, not an ongoing hazard; (2) the download can vanish with zero warning since there's no commercial relationship obligating Jawset to keep it up. **Mitigation for (2), and the actual action item: download and archive a local copy of the Studio installer now, while it's free** — a frozen binary already on disk can't disappear. Given that, Postshot Studio is back on the table as a real `SplatBackend` candidate worth testing, not ruled out — evaluate it alongside Nerfstudio rather than defaulting past it. We genuinely don't know which scenario (active churn vs. frozen abandonware) is true; the installer-archive move is cheap and correct either way.

**Correction to the above (2026-07-13, later same session):** the installer archival was and remains a good, genuinely free move — downloading Postshot costs nothing regardless of tier. What's NOT free, per the pricing-page correction, is unlocking Studio-tier features (the CLI) for actual use. The `--login`/`--password` flags the other verification pass found on the CLI are almost certainly the Studio license/activation check, not an optional extra — meaning unattended `SplatBackend` automation via Postshot would require an active paid subscription tied to those credentials, not just a downloaded binary. Given Nerfstudio's Apache-2.0 status has zero equivalent cost, this materially strengthens the Nerfstudio recommendation over Postshot for anything meant to run unattended — Postshot's remaining honest use case is Sandra manually running the GUI (which the Free tier does support) for one-off high-quality captures, not the CLI-driven automation this server needs.

**Done, 2026-07-13:** installer archived at `D:\Dev\archives\postshot\` on Goliath (Authenticode-verified: signed by "Jascha Wetzel, Munich, DE", matching the site's own imprint exactly — legitimate, not tampered). Turned out Postshot 1.1.0 was **already installed** on Goliath (`C:\Program Files\Jawset Postshot\bin\`, build dated 2026-05-13, predates this investigation) — verified working, not just present:

```
> postshot-cli.exe --version
Postshot v1.1.0 (2026-05-13)

> postshot-cli.exe --help
Subcommands: train, export
```

**Ground-truth confirmation of the collider-mesh finding** (previously sourced from write-ups, now from the actual `--help` output): `export`'s only output option is `--export-splat` (PLY or SPZ). No mesh, no collider, nothing geometry-adjacent in the CLI at all — the earlier secondary-source research was accurate, now verified directly.

**New from the real CLI, not previously known:** `train` takes `--import` (images/video/poses/point-clouds), a real depth of tuning flags (`--profile {Splat ADC, Splat MCMC, Splat3}`, `--splat-density`, `--max-num-splats`, crop/ROI boxes, sky-model generation, anti-aliasing), and outputs a `.psht` project file that `export` then reads from separately — a real two-stage `train` → `export` pipeline, scriptable. Also present: `--login`/`--password` flags on the CLI, meaning even the free tier may want an activation check before training actually runs — **untested, next thing to verify** before assuming this works fully unattended.

**Load-bearing finding, not a nice-to-have:** none of the three produce a collider mesh as a clean sidecar the way worldlabs-mcp's `collider_mesh_url` does. This means the ⚠️ warning above ("route through `blender-mcp`'s `blender_splatting` before Resonite") is **mandatory for any of these three**, not a fallback for edge cases — budget it as a required pipeline stage in whatever implements `SplatBackend`.

`splat_engine_status` tool reports this live. Set `SPLATMAKER_ENGINE` env var once one is chosen — but the actual subprocess/API wrapper in `server.py`'s `SplatBackend` class still needs to be written; the env var alone does not make generation work.

## ⚠️ Important: collision mesh

Unlike worldlabs-mcp (which returns `assets.mesh.collider_mesh_url` alongside every splat), **FOSS splat pipelines generally do NOT produce a collision mesh.** Any consumer of this server's output (Blender, Resonite) needs to route the raw splat through `blender-mcp`'s `blender_splatting` tool to generate a usable collision mesh **before** it's usable in a VR world — skipping this step produces a splat that looks correct in a screenshot and has no floor to stand on. See `mcp-central-docs/architecture/FLEET_DEEP_ANALYSIS_2026-07-13.md` §2.2.1 for the full reasoning (this exact mistake was made once already for worldlabs, in the opposite direction — don't repeat it here).

## Tools

- `splat_generate` (portmanteau) — ops: `from_video`, `from_images`, `status`, `list`, `get_asset`
- `splat_engine_status` — reports which engine is configured

## Ports

- Backend (FastMCP HTTP `/mcp` + `/api/health`): **11091**
- Frontend (Vite React dashboard): **11092**

Registered in `mcp-central-docs/operations/WEBAPP_PORTS.md`.

## Quick start

See `INSTALL.md`. Short version: `uv sync`, then `uv run splatmaker-mcp` (stdio) or `uv run splatmaker-mcp --http` (HTTP on :11091).

## Roadmap

1. ~~Archive a local copy of the Postshot Studio installer~~ **DONE 2026-07-13** — Postshot v1.1.0 (build 2026-05-13) was already installed on Goliath at `C:\Program Files\Jawset Postshot\bin\`; installer archived to `D:\Dev\archives\postshot\`, Authenticode-verified (signed by Jascha Wetzel, Munich — matches the site imprint). CLI tested directly: `postshot-cli.exe train`/`export` work, no mesh export confirmed hands-on. **Pricing corrected 2026-07-13 (see "Engine status" above): Studio is paid (~£40/mo), not free — the CLI's `--login`/`--password` flags are almost certainly the license gate.** Given that, implement against **Nerfstudio** (Apache-2.0, genuinely free, real CLI) — comparison lives in `mcp-central-docs/projects/gestating-chains/medium-chains.md`.
2. Write the real `SplatBackend.generate_from_video`/`generate_from_images` implementations for that engine.
3. SQLite job persistence (v1 is in-memory only — jobs don't survive a restart).
4. Webapp: Gallery, Generate, Jobs pages per `WEBAPP_SOTA_STANDARDS.md`.
5. MCPB packaging + `glama.json` (stub present, needs real health/tier data once engine is wired).
6. If pursuing public release: naked-PC install testing, README screenshots, community-facing docs pass.
