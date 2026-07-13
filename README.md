# splatmaker-mcp

**Self-hosted, zero-marginal-cost Gaussian-splat generation.** The FOSS alternative to worldlabs-mcp's Marble API — point it at a video or a set of images, get a navigable 3D Gaussian-splat world back, run entirely on local hardware (RTX 4090).

**Status: scaffold, v0.1.0.** Server shell, tool schemas, job tracking, fleet health/registration contract, and webapp skeleton are real and working. **The splat-generation engine itself is not yet wired** — see "Engine status" below. This is deliberate (Implementation Honesty Standard), not an oversight: the tools exist and respond honestly with `not_implemented` rather than faking success.

## Why this exists

worldlabs-mcp (Marble API) isn't cheap. This fleet has an RTX 4090 sitting idle for exactly this kind of workload. A FOSS Gaussian-splat pipeline (Postshot / gsplat / Nerfstudio-class tooling — none chosen yet) wrapped as an MCP server gets the same "photo/video → navigable 3D world" capability at zero marginal cost, feeding the same downstream chain (`blender-mcp` → `resonite-mcp` / Resonite, VRChat) that worldlabs-mcp already feeds.

There's also a plausible case this is useful beyond this fleet — the Resonite and VRChat world-building communities currently either pay for splat SaaS or fight research-grade CLI tooling directly. If this ships clean, it may be worth public release per `FLEET_PROMOTION.md`.

## Engine status

| Engine | Status |
|---|---|
| Postshot CLI | Not evaluated |
| gsplat | Not evaluated |
| Nerfstudio-derived | Not evaluated |

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
