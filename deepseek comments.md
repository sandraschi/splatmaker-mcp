# DeepSeek V4 Flash — splatmaker-mcp cross-examination

Read-only review, 2026-07-13. Repo was actively being built by Sonnet in another window; I was asked to look, not touch.

## The thesis

Self-hosted Gaussian-splat generation as a FOSS alternative to World Labs' Marble API,
running on the fleet's RTX 4090 at zero marginal cost, feeding the same downstream chain
(blender-mcp → resonite-mcp) that worldlabs already feeds.

This is sound. The fleet has a paid-cloud bottleneck at the entry point of the VR chain;
splatmaker is the correct mechanical fix for it. The README already traces the pipeline
implications correctly — notably that the `blender_splatting` collider-mesh step shifts
from fallback to primary path, since FOSS splat tools don't ship a collision mesh in the
response the way Marble does. The deep analysis doc (§2.2.1 forward note) already predicted
this repo existing.

## The real question: splat quality vs. worldlabs

The splat itself — the raw Gaussian point cloud — will be competitive. 3DGS is published
math; Nerfstudio's Splatfacto benchmarks at 27.9 dB PSNR on standard scenes. Marble's
internal pipeline is almost certainly derived from the same family of techniques with
engineering optimizations (faster training loops, better view selection heuristics, tuned
hyperparameters). The delta per-splat is real but small — a few dB, not a categorical gap.

The "miraculous" part of worldlabs is not the splat. It's:

1. **Prompt → spec pipeline.** A multi-stage LLM refinement that turns "Venetian cafe at dusk"
   into a structured 20-line scene description with lighting, composition, camera paths, and
   spatial layout. This is the hard part and it's wholly invisible from the output — you just
   see a great scene and assume the splat engine did it.
2. **Collider mesh baked into every response.** One API call, two assets back (splat + GLB).
   FOSS pipelines don't have this, and it's not trivial to add (mesh extraction from splats
   is an active research area).
3. **Scale.** They run on A100s. The 4090 queues jobs sequentially.

## The opportunity (why local beats cloud here)

World Labs' pipeline is a one-shot API. You send a prompt, you get a splat. If you don't
like it, you pay again and hope. splatmaker can do things Marble cannot:

- **Iterative refinement with the user.** Generate → show → "more canal, less gondola" →
  regenerate. The LLM prompt-spec engine is right there in the same process, not behind
  a stateless REST call.
- **Custom priors from your own data.** Photos of your actual room, your workshop, your
  robot's environment. Fine-tune the scene description model on splats you already know
  work for Resonite. World Labs can't do this.
- **Closed-loop editing.** Splat → Blender → edit geometry → re-splat. Since everything
  is local, you can iterate on the mesh and regenerate without leaving the pipeline.
  Marble's output is a terminal artifact; splatmaker's is a work-in-progress.

## What it needs that isn't scaffolded yet

The Nerfstudio engine decision is made (right call). What's not designed is the
**prompt-to-spec module** — the LLM layer that turns free text into a structured scene
description that feeds `ns-process-data`. This is the lever that determines whether
splatmaker produces "good splats" or "splats that feel like places." The scaffold's
current interface (`splat_generate(operation="from_video")`) assumes you already have
captured media; the value multiplier is in `operation="from_prompt"`.

The fleet has everything needed to approximate World Labs' pipeline:
- Ollama on 11434 for the LLM call (fleet standard, already available)
- structured output support via FastMCP/Pydantic for the scene spec schema
- the same `ctx.sample()` pattern the rest of the fleet uses for agentic refinement

The 80/20 bet: 80% of the worldlabs experience at zero marginal cost, with the remaining
20% (the genuine novelty in Fei-Fei Li's team's scene composition priors) being something
we can't match without equivalent scale. That's still a trade worth making.

## One architectural thought for when the engine gets wired

Consider whether `SplatBackend` should be a **plugin registry** rather than a single
engine selection. Right now it's an enum + env var. If you ever want to support both
Nerfstudio (automated CLI pipeline) and Postshot (GUI-assisted high-quality captures
when Sandra wants to be in the loop), the current design needs a refactor. A
`SplatBackend.register("nerfstudio", NerfstudioBackend())` pattern at startup handles
both cleanly from day one. Not urgent at scaffold stage, but the interface is small
enough to change now without pain.

## Post-3DGS paper landscape (added 2026-07-13, after Sandra asked)

The original Kerbl et al. 3DGS paper is July 2023. I searched arXiv systematically
for every significant algorithm-level improvement since. Here is what exists and what
it means for the quality gap.

### The important ones, organized by what they fix

**Anti-aliasing and view consistency:**
- Mip-Splatting (2311.16493, Nov 2023) — 3D smoothing filter + 2D Mip filter, fixes
  the shimmering/aliasing across zoom changes that vanilla 3DGS is terrible at.
- StopThePop (2402.00525, Feb 2024) — hierarchical per-pixel sort, eliminates popping
  artifacts on view rotation. Nerfstudio partially has this in gsplat's renderer.
- Spectral-GS (2409.12771, Sep 2024) — spectral entropy analysis of covariance, better
  high-frequency detail without needle artifacts.

**Densification and pruning (the adaptive control was always the weakest part of 3DGS):**
- AbsGS (2404.10484, Apr 2024) — fixes "gradient collision" where opposing view gradients
  cancel out, replacing mean-length gradient with homodirectional view-space positional
  gradient. Directly improves fine detail recovery.
- Mini-Splatting (2403.14166, Mar 2024) — blur split + depth reinit, keeps quality under
  constrained Gaussian budgets.
- **3DGS-MCMC** (2404.09591, Apr 2024) — treats Gaussians as MCMC samples, SGLD updates
  replace the heuristic clone/split entirely. Principled densification with controllable
  count and robust initialization. This is the most theoretically clean improvement.
- Compact-3DGS (2606.21244, Jun 2026) — momentum-guided densification, 3.7x training
  speedup, 0.89 dB PSNR gain. Very recent.

**Geometry and surface quality:**
- **2DGS** (2403.17888, Mar 2024) — oriented planar disks replace 3D ellipsoids, ray-splat
  intersection, depth distortion + normal consistency. Gives actual surface accuracy and
  mesh extraction, not just a point cloud with good novel views.
- SuGaR (2311.12775, Nov 2023) — regularizer that aligns Gaussians to surfaces, Poisson
  mesh extraction.
- **Scaffold-GS** (2312.00109, Dec 2023) — anchor points distribute local Gaussians with
  on-the-fly attribute prediction per view direction. View-adaptive quality with reduced
  redundancy. This is the one I would wire first.
- Deformable Beta Splatting (2501.18630, Jan 2025, SIGGRAPH 2025) — Beta kernels replace
  Gaussians entirely, 45% fewer parameters, 1.5x faster than MCMC. Academic progress but
  not yet in any stable pipeline.

**Feed-forward / generalizable (the World Labs speciality):**
- pixelSplat (2312.12337, Dec 2023) — predicts dense depth from image pairs, feed-forward
  Gaussian prediction.
- MVSplat (2403.14627, Mar 2024, ECCV 2024) — cost volume plane sweeping, 10x fewer
  params than pixelSplat, 2x faster.
- Splatter Image (2312.13150, Dec 2023, CVPR 2024) — one Gaussian per pixel from a single
  image, 38 FPS inference.

**Compression:**
- LightGaussian (2311.17245, Nov 2023, NeurIPS 2024) — 15x compression, 200+ FPS.
- HAC (2403.14530, Mar 2024, ECCV 2024) — hash-grid context modeling, 75x compression,
  HAC++ pushes to 100x.

### What Nerfstudio/gsplat already has

Mip-Splatting anti-aliasing and basic gradient pruning. That's about it. Everything
else on the list above — Scaffold-GS, 2DGS, MCMC, AbsGS, Mini-Splatting, SuGaR,
pixelSplat, LightGaussian, HAC — is **not** in Nerfstudio's default Splatfacto pipeline
as of mid-2026.

### What World Labs almost certainly has (and won't publish)

Their math team (Mildenhall, Li, Johnson, Lassner) has two years of head start and
the resources to train large-scale feed-forward models. The bet is they have:

1. A **proprietary feed-forward Gaussian predictor** — akin to pixelSplat/MVSplat but
   trained on millions of scenes with vision foundation model priors, not just 1,000-image
   datasets. This is what makes their API feel instant — it's not per-scene optimization,
   it's learned inference.
2. **Diffusion-based inpainting** for unseen regions, since feed-forward prediction is
   sparse and hallucination is the only way to fill occluded areas.
3. **Reflection/specular decomposition** — this is hard for all GS methods and they may
   have dedicated networks.
4. **Tuned hyperparameters at scale** from processing thousands of user scenes, which is
   a data moat no paper can close.

### What this means for splatmaker

**The improvements that matter most for a local 4090 pipeline, in order of ROI:**

1. **Scaffold-GS** — replaces the flat Gaussian field with anchor-based prediction. Better
   quality per-Gaussian, less redundancy, view-adaptive detail. Single biggest quality
   lift for the least implementation cost. Nerfstudio does not have this; wiring it means
   forking or replacing Splatfacto.
2. **MCMC densification** — replaces the heuristic clone/split with something principled.
   Fewer artifacts, more stable training, controllable Gaussian count. Compatible with
   Scaffold-GS.
3. **2DGS** — if you want actual surfaces (meshes, collision geometry) from the splat,
   this is the right representation. The README's concern about collider mesh is directly
   addressed by 2DGS, which produces extractable surfaces as a natural output.
4. **AbsGS** — cheap to add, directly improves fine detail. Drop-in compatible with
   existing 3DGS/Scaffold-GS.

**The gap that no paper closes:**

No amount of optimization-loop improvements gets you feed-forward inference from 3 input
views. That requires large-scale pre-training, which requires data and GPU-hours that a
4090 cannot provide. World Labs' feed-forward pipeline is the genuine moat — not because
their splats look better given dense input, but because they look *as good* from 3 photos
as a local pipeline looks from 50. For splatmaker's primary use case (video captures,
multi-image sets where the user can take 50+ photos), this advantage is irrelevant.

**Revised bottom line on quality:**

Wire Scaffold-GS + MCMC + AbsGS on top of Nerfstudio's engineering infrastructure and
you get a local pipeline whose per-scene optimization quality **exceeds** Marble for the
same dense input — because Marble's feed-forward model trades per-scene fidelity for
speed and sparsity, and those tradeoffs become visible when you have enough input views.
The "miraculous" quality of worldlabs outputs is real but bounded: it comes from their
prompt-to-spec engine and their robustness to sparse input, not from fundamentally better
splatting math. The improvements are published, replicable, and waiting to be wired.
