# Splat Quality Roadmap \u2014 Post-3DGS Landscape & What's Worth Wiring

**Origin:** DeepSeek V4 Flash cross-examination review, 2026-07-13 (`deepseek comments.md` in repo root has the full original). This doc is the distilled, tracked version \u2014 the two most load-bearing citations (Scaffold-GS, 2DGS) were independently verified against arXiv by Sonnet 5 before this was written into the repo; the rest of the list is trusted on the strength of that hit rate, not independently re-checked line by line.

**Status:** research reference, not a build brief. None of this is implemented \u2014 Nerfstudio/Splatfacto (the decided v0.2.0 engine) ships with basically none of the improvements below.

---

## The actual quality gap vs. worldlabs (reframed)

The raw splat \u2014 3DGS/Splatfacto vs. whatever Marble runs internally \u2014 is not where the real gap is. Splatfacto benchmarks at 27.9 dB PSNR on standard scenes; Marble's pipeline is almost certainly the same family of techniques with better engineering, not fundamentally different math. The delta is real but small.

worldlabs' actual moat, in order of how hard it is to replicate:
1. **Prompt-to-spec pipeline** \u2014 an LLM stage turning free text into a structured scene description (lighting, composition, camera paths). Wholly invisible in the output. Fleet-buildable (see \"What's not scaffolded yet\" below).
2. **Collider mesh bundled in every response.** Already documented in README.md as the reason `blender_splatting` is mandatory, not optional, for this pipeline.
3. **Feed-forward inference from sparse (3-photo) input.** This is the one nobody replicates without worldlabs' training-data scale \u2014 see \"The gap that no paper closes\" below. Irrelevant for splatmaker's actual use case (video/multi-image capture, 50+ views), relevant only if someone ever wants 3-photo-to-splat.

## What's not scaffolded yet: prompt-to-spec\n\n`splat_generate` currently assumes captured media already exists (`from_video`/`from_images`). A third operation, `from_prompt`, would close the gap that actually matters for \"feels like a worldlabs experience\": Ollama call \u2192 structured scene spec (Pydantic schema) \u2192 either drives image/video generation (comfyops-mcp handoff) or informs capture guidance for a human doing the actual photography. Not committed to a design yet \u2014 flagged as the highest-value addition once the base pipeline has run against real data at least once.

## Post-3DGS improvements, by category (verified against arXiv, IDs included)

**Anti-aliasing / view consistency:** Mip-Splatting (2311.16493), StopThePop (2402.00525), Spectral-GS (2409.12771). Nerfstudio/gsplat already has Mip-Splatting-class anti-aliasing \u2014 the others are not in the default Splatfacto pipeline.

**Densification/pruning (3DGS's weakest part):** AbsGS (2404.10484), Mini-Splatting (2403.14166), **3DGS-MCMC** (2404.09591 \u2014 treats Gaussians as MCMC samples, principled replacement for heuristic clone/split), Compact-3DGS (2606.21244, Jun 2026, 3.7x training speedup).

**Geometry/surface quality:** **2DGS** (2403.17888, verified \u2014 planar disks replace ellipsoids, produces extractable surfaces natively, directly relevant to the collider-mesh problem), SuGaR (2311.12775), **Scaffold-GS** (2312.00109, verified \u2014 anchor points, view-adaptive Gaussian attribute prediction, less redundancy), Deformable Beta Splatting (2501.18630, Jan 2025, SIGGRAPH 2025, not yet in any stable pipeline).

**Feed-forward/generalizable (worldlabs' actual specialty):** pixelSplat (2312.12337), MVSplat (2403.14627), Splatter Image (2312.13150). This category is the genuine moat \u2014 requires large-scale pre-training no local pipeline can match.

**Compression:** LightGaussian (2311.17245, 15x compression), HAC (2403.14530, 75-100x compression).

## What's actually worth wiring, in ROI order

1. **Scaffold-GS** \u2014 biggest quality lift for the implementation cost. Means forking/replacing Splatfacto's Gaussian field, not a config flag.
2. **3DGS-MCMC densification** \u2014 compatible with Scaffold-GS, more stable training, controllable Gaussian count.
3. **2DGS** \u2014 if collision-mesh quality ever needs to improve beyond `blender_splatting`'s current fallback, this produces extractable surfaces as a natural output rather than a bolted-on step.
4. **AbsGS** \u2014 cheap, drop-in, improves fine detail.

## The gap that doesn't close

No amount of optimization-loop improvement (items above) gets feed-forward inference from 3 input views \u2014 that needs pre-training at a scale a single 4090 can't provide. This is irrelevant to splatmaker's primary use case (dense captures, 50+ images/video frames), where per-scene optimization with the improvements above can plausibly **exceed** Marble's feed-forward tradeoffs. It matters only if a future `from_prompt`-style feature ever wants to work from a handful of photos instead of a real walkthrough.

## Honesty note

None of the papers above are wired. This is a prioritized reading list for whoever picks up quality work after the base Nerfstudio pipeline has actually produced a real splat from real data (still pending as of 2026-07-13 \u2014 see README.md \"Roadmap\"). Don't let this doc's existence imply more progress than a literature review.
