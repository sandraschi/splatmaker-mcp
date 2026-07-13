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
| License | Apache-2.0 | Apache-2.0 | Proprietary. Verified live on jawset.com 2026-07-13: all three tiers (Free/Indie/Studio) are €0.00/month. Was paid as recently as Feb 2026 (Indie ~€17/mo), reset to free in an undocumented restructure. Single-maintainer sole proprietorship (Jascha Wetzel, Munich, Germany) — real bus-factor/reversal risk, not a funded company |
| Language | Python + CUDA | Python + CUDA (via gsplat) | Not published, native Windows app |
| CLI | None — write your own training script | Real CLI: `ns-process-data`, `ns-train`, `ns-export`, `ns-render` | GUI-first; CLI historically gated to paid Studio tier |
| **Collider mesh sidecar** | **No** — pure rasterizer | **Partial** — `ns-export tsdf`/`poisson`, separate command, untested against Splatfacto specifically | **No** — PLY splat + camera poses only |
| Speed (RTX 4090) | ~8 min (fastest) | ~10 min | ~30 min (different benchmark scale) |
| VRAM | ~4GB | ~6GB | Not specified |
| Quality (PSNR, same benchmark) | 28.1 dB | 27.9 dB | Not benchmarked head-to-head |
| Known gaps | JIT CUDA compile breaks on some PyTorch/CUDA combos; zero pipeline, all DIY glue | No fisheye/equirectangular/orthographic camera support (perspective only) — check against actual capture method | PLY exports have been reported missing attributes (normals, opacity, scale, rotation, SH coefficients) needed by some downstream tools (SOGS) |

**Working recommendation (not yet implemented):** Nerfstudio — real CLI suited to subprocess wrapping, fully Python (fits fleet's `uv`-first philosophy, zero extra glue vs. gsplat), PSNR gap vs. alternatives is within "barely perceptible" range per every source checked. Postshot's GUI-first design and historically-paywalled CLI make it a weaker fit for unattended MCP dispatch despite being the nicest hand-driven tool.

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

1. Pick an engine (Postshot vs gsplat vs Nerfstudio) — comparison lives in `mcp-central-docs/projects/gestating-chains/medium-chains.md`.
2. Write the real `SplatBackend.generate_from_video`/`generate_from_images` implementations for that engine.
3. SQLite job persistence (v1 is in-memory only — jobs don't survive a restart).
4. Webapp: Gallery, Generate, Jobs pages per `WEBAPP_SOTA_STANDARDS.md`.
5. MCPB packaging + `glama.json` (stub present, needs real health/tier data once engine is wired).
6. If pursuing public release: naked-PC install testing, README screenshots, community-facing docs pass.
