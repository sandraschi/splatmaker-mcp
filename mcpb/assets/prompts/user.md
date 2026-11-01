# splatmaker-mcp — User Guide

Welcome. splatmaker-mcp turns your own photos or a walk-around video into a
navigable photorealistic 3D world — a Gaussian splat — computed entirely on
your own hardware, with no per-scan fees and nothing uploaded anywhere. This
guide walks you from zero to your first splat and answers the questions that
come up along the way. Keep the Help page in the webapp open beside it; both
say the same things, and the product is the authority if they ever disagree.

## 1. What you actually got

Three things work together. The **engine** is Nerfstudio, a free
open-source 3D-reconstruction toolkit from UC Berkeley, run here through its
Splatfacto method. The **server** wraps that engine: it accepts your media,
runs the multi-minute reconstruction in the background, tracks every attempt
as a job, and answers questions about engine health. The **webapp** (11
pages) is the friendly face: start jobs, watch them, read logs, browse
finished splats, chat with a local AI about the process, and learn the
workflow. A fourth piece, **chat**, is answered by your own Ollama models —
no cloud, no key, no telemetry.

What you did not get, and should not expect: a one-click magic button, a
collision mesh (see §7 — no free splat pipeline makes one), an embedded 3D
viewer, or cloud processing. Every limitation below is stated where you will
hit it, not buried.

## 2. Install and start

You need Python 3.12, uv, Node tooling for the webapp (bun is the fleet
standard, npm also works), and — for actual training — an NVIDIA GPU with
CUDA plus the engine packages. The base install (server + webapp, no engine)
is enough to explore every page except real generation.

```powershell
cd D:\Dev\repos\splatmaker-mcp
uv sync --extra dev        # base + tooling
```

Engine (one time, large — hundreds of packages including PyTorch with CUDA,
roughly 10 GB):

```powershell
uv sync --extra engine      # THE only correct engine install
uv run --extra engine ns-train --help   # must exit 0; prints help
```

Read that warning twice: a plain `uv sync` without `--extra engine`
silently *uninstalls* the engine packages again, because uv reconciles the
environment to the default set and treats extras as surplus. If generation
ever breaks with missing-module errors (`absl`, `appdirs`, `tensorboard`
pieces), the cause is almost always a bare sync that stripped the env — run
`just sync-engine` (or the two commands above) and restart the backend.
This exact failure happened on 2026-11-01 and cost an afternoon; the Status
page now proves engine health with a cached `ns-train --help` probe instead
of trusting that files exist.

Starting:

```powershell
uv run splatmaker-mcp                 # stdio (Claude Desktop / Cursor)
uv run splatmaker-mcp --http         # HTTP backend :11091, or start.ps1 for both tiers
```

Claude Desktop config snippet (stdio):

```json
{
  "mcpServers": {
    "splatmaker": {
      "command": "uv",
      "args": ["run", "--project", "D:/Dev/repos/splatmaker-mcp", "splatmaker-mcp"],
      "cwd": "D:/Dev/repos/splatmaker-mcp"
    }
  }
}
```

The webapp serves on :11092 (Vite dev) or from `webapp/dist` after `bun run
build`. The Tauri desktop shell wraps the same frontend. Ports are
11091/11092 by default (`SPLATMAKER_PORT` / `MCP_PORT` override the backend).

## 3. What is Nerfstudio, really

Nerfstudio is a research-grade but genuinely usable framework for turning
2D captures into 3D scenes. You give it many overlapping views of one real
space; it figures out where each photo was taken (camera poses, via COLMAP
under the hood) and then optimizes a 3D representation until renders from
those viewpoints match your photos. The representation used here is a
**Gaussian splat**: millions of soft, translucent 3D blobs (position, size,
color, opacity each), which render fast and look photographic from any
angle you move to — that is the "navigable world" feel.

The three commands the server runs for every job:

1. `ns-process-data images|video --data <in> --output-dir <processed>` —
   ingest + pose estimation. Fails here = your media is the problem
   (unreadable files, empty folder, no overlap between shots).
2. `ns-train splatfacto --data <processed> ... --max-num-iterations 15000
   --vis tensorboard --viewer.quit-on-train-completion True` — the actual
   optimization, ~10 minutes on an RTX 4090 at the default 15k iterations
   (half of Nerfstudio's own 30k default — a deliberate speed/quality
   tradeoff; raise `SPLATMAKER_MAX_ITERATIONS` toward 30000 for hero
   quality). Tensorboard logging, not the interactive viewer, because
   nothing connects to a viewer socket in unattended runs.
3. `ns-export gaussian-splat --load-config <config.yml> --output-dir
   <export>` — writes the `.ply` point/blob file. This file IS the splat.

The alternative engines the project evaluated and rejected: bare `gsplat`
(CUDA rasterizer library, no CLI, all pipeline glue would be hand-written)
and Postshot (proprietary app whose automation CLI sits behind a paid tier).
Nerfstudio won on: free license, real CLI, Python throughout, good-enough
quality (about 28 dB PSNR on standard benchmarks, a hair under pure gsplat).

## 4. Your first splat, step by step

1. **Capture.** One folder of sharp, overlapping phone photos of a single
   space (aim for 60–80% overlap between neighbors, all roughly the same
   height, even lighting, nothing moving), or one slow walk-around video.
   See §5 for the full capture discipline — capture quality decides output
   quality more than any setting.
2. **Generate page.** Choose video or images, point at your files, start.
   You get a job id instantly; training runs in the background.
3. **Jobs page.** Watch the status move `queued → running → done` (minutes,
   not seconds). The page polls every 5 seconds. Go make coffee.
4. **Gallery page.** The finished job lands here with its `.ply` path.
   Open the `.ply` in SuperSplat (free, browser-based) to fly through it.
5. **Collider step.** Before any VR use: route the `.ply` through
   `blender-mcp`'s `blender_splatting` to generate a collision mesh. A splat
   without a collider looks perfect and has no floor — everyone learns this
   exactly once, preferably from this paragraph instead of from falling
   through the world in front of friends.

Example dialogue:

> You: "I walked around my living room with my phone, one video, about two minutes. What now?"
> Assistant: "Put the video somewhere stable, open Generate, choose from_video, paste the path, start. You'll get a job id — the Jobs page will show it running for roughly ten minutes. When it's done, Gallery gives you the .ply. Before VRChat, we route it through blender-mcp for the collider."

> You: "It's been running 20 minutes, is it stuck?"
> Assistant: "Check the Jobs page message line. `running` with no message is normal — stages only report at boundaries. Past ~25 minutes on a 4090 for a small scene, suspect VRAM pressure or bad poses; read Inbox if it failed — the message names the stage and the stderr tail."

## 5. Capture guide (the part that actually decides quality)

- **Overlap is everything.** Every point of the scene should appear in at
  least three photos. Walk a grid, not a circle: two heights (standing +
  crouch) beats one orbit.
- **Lock exposure.** Tap-hold focus/exposure lock on phones; auto-exposure
  pumping between frames confuses pose estimation more than slight blur.
- **Even light, no motion.** Overcast daylight or all-room-lights-on beats
  mixed sun/shadow. People, pets, and ceiling fans must leave the set.
- **Video:** 4K if you have it, slow and smooth (a cheap gimbal or two
  hands), 1–3 minutes for a room. The server takes the file as-is;
  `ns-process-data video` extracts frames itself.
- **What fails:** textureless white walls (nothing to match), mirrors and
  windows (reflections move), drone-style top-down-only coverage (no
  eye-level parallax), 12 photos of a whole house (not enough views).
- **How many:** 80–200 photos for a room is the sweet spot. More helps up
  to a point; beyond ~400 you are mostly buying training minutes.

Example dialogue:

> You: "Half my photos are blurry, is the set usable?"
> Assistant: "If a third are sharp with good overlap, yes — drop the blurry ones, keep one folder of the sharp set, and submit that. Blurry frames actively hurt poses; fewer good views beat many mixed ones."

## 6. Jobs: statuses, polling, and the Inbox

A job is one generation attempt, forever recorded in SQLite (survives
restarts). `queued` = accepted and starting. `running` = a stage is
executing (which stage shows in the message line when stages report).
`done` = `.ply` on disk, fetch it from Gallery. `failed` = read the message
— it names the stage (`ns-process-data`, `ns-train`, `ns-export`,
`staging`) and the stderr tail — fix the input, start a new job.

The **Inbox** page exists so failures are never silent: failed jobs with
their messages, plus in-flight jobs so you do not launch a second VRAM-hungry
training on top of the first. Two concurrent `ns-train` runs on one 4090
will crawl or OOM-kill each other — generate serially unless you accept the
slowdown. There is no server-side queue; `queued` means starting now.

`get_asset` (Jobs → Gallery path) only works on `done` jobs and returns
`ply` (the deliverable), `config` (training config, keep for provenance),
`job_dir` (the whole run: processed data, checkpoints, exports — the
debugging gold for repeats).

## 7. Using your .ply (Gallery, viewers, VR)

The Gallery lists finished jobs with their `.ply` paths. A `.ply` here is a
Gaussian-splat file (positions + scales + colors + opacities + spherical
harmonics), not a mesh — regular mesh tools will show a point cloud at best.
Open it in **SuperSplat** (free, in-browser) to inspect and fly through, or
import it into Blender (via a splat importer) for cleanup and rendering.

For VR (Resonite, VRChat): the mandatory chain is `.ply` → `blender-mcp`
`blender_splatting` (collision mesh) → world import. Budget this as a real
pipeline stage, not an edge case. Skipping it is the single most common
splat failure mode fleet-wide, in both directions (once, a team assumed a
paid API's mesh would exist and it did not; here the mesh genuinely does not
exist — same outcome).

## 8. Chat page

The Chat page talks to your own Ollama models — the model picker lists what
is installed locally (completion-capable ones), history persists in the
browser, Enter sends. It is a process companion, not the generator: it
answers "what does this error mean", "how should I re-shoot this room",
"what is Nerfstudio", and it knows the workflow, but generation itself
always goes through Generate (a chat message cannot start training, by
design — slow GPU work deserves an explicit button).

Example dialogue:

> You: "What is Nerfstudio and why do I need a GPU?"
> Assistant: "Nerfstudio is the free engine that turns your photos into the 3D scene — it optimizes millions of 3D blobs until renders match your photos. That optimization is massively parallel number-crunching, which is what GPUs are for; on a CPU the same room would take hours instead of ~10 minutes. The GPU requirement is physics, not upselling."

> You: "ns-train failed, message mentions CUDA out of memory."
> Assistant: "Lower SPLATMAKER_MAX_ITERATIONS (try 8000) and re-run, or use fewer input images. Close anything else holding VRAM. The failed job kept its processed data in job_dir, so the retry skips straight to training."

If the model list is empty, Ollama is down — start it (`ollama serve`) and
refresh. If an answer about YOUR jobs sounds off, check Jobs/Inbox — the LLM
does not read the job store live; the pages do.

## 9. Tools, Skills, Logs, Settings tour

- **Tools** renders the live tool catalog from `/api/capabilities` (the
  four MCP tools with their operations) plus the REST list. New server
  version, new tools? This page updates itself — nothing hardcoded.
- **Skills** shows the `splat_workflow` prompt text (the five-step briefing
  agents receive) and the `splatmaker://jobs` resource descriptor.
- **Logs** is the server's in-memory ring (last 500 lines, 5 s polling,
  Refresh button) — backend warnings, hub registration, subprocess stages.
  First stop when "it broke and Jobs says nothing".
- **Settings** shows live engine state (configured / verified / version /
  iterations) plus the environment-variable table. Verification can read
  `pending` for the first minute after backend start while the background
  `--help` probe runs — that is normal, not broken.
- **Dashboard** is the at-a-glance view: backend dot, engine card, job
  counts, CTAs — plus a red banner linking here whenever the engine is not
  verified-ok.

## 10. Troubleshooting

- **Engine `verified: broken`, missing-module error** → env pruned by a bare
  sync. `just sync-engine` (or `uv sync --extra engine`), restart backend,
  wait ~60 s for the probe. Dashboard banner links here.
- **Engine `verified: missing`** → CLI not installed at all: `just
  sync-engine`, confirm `ns-train --help` exits 0 in the venv.
- **`verified: pending` for many minutes** → backend restarted recently, or
  the probe thread is starved; check Logs. Do not re-sync blindly.
- **Unstyled webapp (plain HTML)** → webapp config changed without a dev
  restart, or a broken build slipped through. Rebuild (`bun run build` must
  pass the CSS gate: ≥ 5 kB, no raw `@tailwind`); restart the dev server
  (its start time must postdate `postcss.config.js`).
- **Port in use (11091/11092)** → a previous backend/frontend is alive.
  Reuse it or stop it cleanly (`POST /api/shutdown` for the backend); never
  run two writers against the job database.
- **`get_asset`: "not done"** → poll `status`; do not re-submit.
- **Train failures** → VRAM (lower iterations) or bad poses (re-shoot with
  more overlap). The job message names the stage; Inbox collects them.
- **Chat empty / errors** → Ollama down (`ollama serve`), or no completion
  model installed (`ollama pull` a small one like llama3.2).
- **Hub 404 in logs** → normal standalone operation (the federation hub has
  no register endpoint); non-fatal by design.

Example dialogue:

> You: "Dashboard shows engine broken, error about tensorboard and absl."
> Assistant: "Classic pruned-env. Run just sync-engine, restart the backend with start.ps1, give it a minute — Status should flip to verified ok with a version. If it stays broken, paste the engine_error line."

## 11. FAQ

**Is my media uploaded anywhere?** No. Capture, training, chat, jobs —
everything stays on this machine (Ollama calls are localhost; the hub
registration is local-only and currently a no-op 404).

**How long does a room take?** Roughly 10 minutes on an RTX 4090 at default
settings, plus pose estimation. Bigger scenes and higher iterations scale up
linearly-ish. The Jobs page is honest about `running`; there is no progress
percent because the trainer does not emit one the server can trust.

**Can I train two scenes at once?** The server allows it; the GPU does not
recommend it. Serial generation unless you enjoy OOM errors.

**Do I need Blender/Resonite accounts?** Blender is free and local; Resonite
and VRChat have their own accounts and import paths. splatmaker-mcp hands
you the `.ply` — what you do with it downstream is your pipeline.

**Why not just pay for a splat API?** You can — WorldLabs Marble and peers
exist. The tradeoff this server makes: zero marginal cost, full privacy, no
queue, against ~10 minutes of your own GPU and a capture discipline you have
to learn. For one-off scans the API may win; past a handful, local wins.

**What is still missing?** An embedded 3D viewer (use SuperSplat), list
filtering on Jobs/Logs, a second engine option (the backend is structured
for a plugin registry but only Nerfstudio exists), MCPB packaging polish,
and a full end-to-end demo run on real capture data (needs real photos —
demo datasets were externally blocked).

## 12. Glossary

- **Gaussian splat / Splatfacto:** the 3D representation (blobs) and the
  Nerfstudio method that computes it.
- **Pose (camera pose):** where each photo was taken, computed by COLMAP
  inside `ns-process-data`. Bad poses = bad splat, always.
- **Iterations:** optimizer steps (`--max-num-iterations`, default 15000
  here vs 30000 upstream). More = sharper, slower.
- **`.ply`:** the export file (positions, scales, colors, opacities). Your
  deliverable.
- **Collider / collision mesh:** the invisible geometry avatars stand on.
  Never emitted here; always built downstream via blender-mcp.
- **Job:** one tracked generation attempt (`queued/running/done/failed`).
- **`verified`:** the cached `ns-train --help` proof on the Status page.
  The only engine-health signal that counts.
- **Extras (`--extra engine`):** the optional-dependency group holding the
  GPU stack. Keep it installed with `just sync-engine`; bare `uv sync`
  removes it.

## 13. Big scenes: houses, gardens, venues

One job equals one reconstruction, and reconstructions degrade as the area
grows — poses drift, VRAM fills, training time climbs. Do not photograph a
whole house as one set and hope. Partition the space into overlapping zones
(one room = one job, gardens split by sightline), capture each zone as its
own folder, and submit one job per folder. Name folders after zones
(`living-room/`, `garden-west/`) because the training experiment name
defaults to the dataset directory name — future-you will thank present-you
when the Gallery holds six `done` jobs.

Overlap BETWEEN zones matters as much as overlap within: finish each zone
with a few shots looking into the next one. You will align the finished
splats downstream (they share no common coordinate frame — each job solves
its own poses independently), so keep one fixed reference visible in every
zone if you can (a doorway, a distinctive corner). Training order: easiest
zone first (small, textured, well-lit) to validate the pipeline end to end,
then the hard ones (glass, white walls, vegetation — vegetation is genuinely
difficult: leaves move and repeat, expect softer results and consider
overcast days when nothing flutters).

Job hygiene at scale: the job store never forgets, and neither should you.
Failed attempts stay listed — that is the point (compare the message across
two failures of the same folder before changing anything; identical stage +
identical tail means identical cause). `job_dir` per job holds processed
data, checkpoints, and exports — disk fills up across dozens of jobs, so
archive finished `job_dir`s you have exported from, and never delete a
`job_dir` whose `.ply` you have not yet opened. Gallery shows finished jobs;
Inbox shows failures; use both as your lab notebook, not just a queue.

Example dialogue:

> You: "I want the whole ground floor — hall, kitchen, living room. One job or three?"
> Assistant: "Three jobs, three folders, with doorway shots shared between neighbors. Run hall first (smallest, validates everything), then kitchen, then living room. Stitch them downstream — the server gives you three good splats, not one mushy one."

## 14. Downstream walkthroughs (SuperSplat, Blender, Resonite, VRChat)

**SuperSplat (inspect, free, browser).** Open SuperSplat, load the Gallery
`.ply`. Fly with WASD + mouse. What to check: floaters (stray blobs in
mid-air = under-observed regions — note where, re-shoot those angles),
exposure seams (brightness jumps between viewpoints = auto-exposure pumped
during capture — lock it next time), and edge falloff (scene dissolving at
borders = capture boundary — walk a wider loop). SuperSplat also crops and
cleans: delete obvious floater selections and re-export before any VR use —
five minutes of cleanup here saves an hour of collider pain later.

**Blender (cleanup + collider).** Import the cleaned `.ply` with a splat
importer, then run `blender-mcp`'s `blender_splatting` stage to generate the
collision mesh from the splat density. Inspect the collider against the
visual: stairs, thresholds, and furniture edges are where auto-colliders
lie. Fix by hand or accept invisible walls in exactly those spots and tell
your users. Export the pair (visual + collider) in whatever your target
world pipeline expects.

**Resonite / VRChat (import).** Both import meshes, not splats, through
their own avatar/world toolchains — check the current importer story for
your platform version before promising dates, because splat import tooling
moves fast and this guide will not chase it. The invariant across all of
them: visual `.ply` first, collider second, walk-test third. Never skip the
walk-test (spawn, walk every room boundary, jump once). The walk-test is
where missing colliders announce themselves, and it takes two minutes.

Example dialogue:

> You: "The splat looks great in SuperSplat but I fall through in Resonite."
> Assistant: "That is the missing collider, exactly as designed — the .ply has no floor. Run blender-mcp blendersplatting on the cleaned .ply, import visual plus collider, walk-test the boundaries. If you still fall through in one spot, the collider missed a thin region there — patch it by hand in Blender."

## 15. For automators (scripts, APIs, repeatability)

Everything clickable exists as REST for scripts: start jobs by posting to
the MCP tool from any MCP client, or drive `POST /api/jobs/status` polls
from a loop. A minimal watcher in PowerShell: start a job, then poll
`/api/jobs/status` every 60 seconds until `done`/`failed`, then fetch the
`.ply` path from Gallery data (`GET /api/jobs` includes `asset_paths`) and
copy it to your archive with the job id in the filename. Keep the
`config.yml` path alongside — it records iterations and data layout, which
is the only provenance a later "why does this one look different" question
can use.

Repeatability notes: same folder + same `SPLATMAKER_MAX_ITERATIONS` gives
structurally similar (not bit-identical) results — training has stochastic
elements. Log which iteration count produced your best splat per zone; when
re-shooting, match it before comparing quality, or you are comparing
settings, not captures. The Status endpoint's `engine_version` belongs in
your lab notes too (a Nerfstudio upgrade can shift quality slightly).

Reading the Logs page like a developer: hub-404 lines are benign
(standalone mode). Subprocess stage lines name the exact command the server
ran — copy it to reproduce a stage by hand in the venv (`uv run --extra
engine ns-train ...`) when diagnosing exotic failures. Ring holds 500 lines;
long trainings roll the earliest lines off, so check mid-run for stage
boundaries rather than only at the end.

Example dialogue:

> You: "I want a nightly script that re-trains the garden every Sunday."
> Assistant: "Script it: fixed folder, fixed iterations, poll to done, archive the .ply with the date. But re-training only helps if the capture changed — same photos in means same-ish splat out. Automate the capture reminder, not just the training."

## 16. Sharing, updates, and knowing when to re-shoot

**Household and LAN use.** The backend binds 127.0.0.1; the webapp talks
same-origin. Anyone on your Tailscale/LAN can use the webapp URL if the
backend listens on the LAN interface — but think twice: one GPU means one
training at a time, and someone else's 400-photo set will sit in YOUR Inbox
as YOUR failed job if their capture is bad. For shared use, agree on one
rule: the submitter owns the Gallery result and the Inbox cleanup. CORS
already permits LAN/Tailscale origins, so no config change is needed — just
the social contract.

**Tauri desktop shell.** The same 11 pages ship as a desktop app (NSIS
installer target). It talks to the same backend on 11091 — start the backend
first, then the app. If the desktop window shows connection errors while the
browser works, the backend is not the problem: check the app can reach
127.0.0.1:11091 (loopback firewalls, VPN kill-switches, and "public network"
profiles are the usual suspects, in that order).

**Updates.** Pull, `uv sync --extra dev`, `uv sync --extra engine` (both —
the second re-asserts the GPU stack after any prune), rebuild the webapp,
restart both tiers. After an update, Status should show the same engine
version unless the lockfile moved — if `engine_version` changed, treat your
next training as a fresh experiment, not a continuation, and say so in your
notes.

**When to stop fixing inputs and re-shoot.** Three failed jobs on the same
folder with three DIFFERENT stage errors means the capture is marginal in
several independent ways — stop tuning and re-shoot. Two failures with the
IDENTICAL error means one cause — fix exactly that (usually: more overlap,
locked exposure, no motion, fewer textureless walls). One failure naming
`ns-process-data` with empty or single-digit matched pairs means the folder
was never viable — no setting rescues zero overlap. The re-shoot checklist,
in order: lock exposure, double the photo count, halve your walking speed,
remove everything that moves, and shoot the boring transitional spaces
(hallways, doorways) you skipped the first time — reconstructions die in the
gaps between rooms, not in the rooms. When in doubt, capture more: storage
is cheap, re-shoots are expensive, and no slider fixes missing viewpoints.
Your tenth splat will embarrass your first — that is the craft working.
