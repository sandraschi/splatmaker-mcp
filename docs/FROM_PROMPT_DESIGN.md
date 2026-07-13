# `from_prompt` Design Sketch - Multi-Step Refiner

**Status:** design sketch, not committed, not scoped for effort/timeline. Origin: Sandra's 2026-07-13 worked example ("Falling Water Villa living room" -> North by Northwest's Vandamm House / Fallingwater). Not a build brief - promote to one when this is actually queued.

## Why the worked example matters

The Vandamm House (North by Northwest, 1959) is fictional - production designer Robert Boyle modeled it *after* Fallingwater, but it was never a real, fully-designed building. It existed only as a partial MGM soundstage set plus a matte painting for exterior shots. This means:

- No complete floorplan of "the movie house" exists - only Fallingwater's real, published floorplans (Frank Lloyd Wright Conservancy), and whatever interior stills survive from the scenes actually filmed.
- A prompt like this is genuinely ambiguous, not a corner case: real Fallingwater vs. cinematic Vandamm interior (partial) vs. a deliberate blend are three different, valid answers depending on what the person meant.
- **This is the normal shape of an evocative architectural prompt, not an edge case.** Any `from_prompt` design has to treat disambiguation as stage one, not skip straight to generation.

## Proposed pipeline

```
Prompt ("falling water villa living room, like north by northwest")
   |
   v
1. DISAMBIGUATION (Ollama, structured output)
   Resolve real-world referent(s). May need to ask a clarifying question
   rather than guess (real building? fictional depiction? blend?) -
   silently picking one is worse than asking once.
   |
   v
2. GROUNDING SEARCH (parallel, tool-assisted)
   - plex-mcp: does the referenced film exist in the library? pull stills
     from the specific scenes that match (interior, not exterior matte
     shots that don't correspond to any real room)
   - web search: real building's published floorplans/archival photos if
     the referent is (partly) real (Fallingwater Conservancy, etc.)
   |
   v
3. SCENE SPEC (Ollama, structured Pydantic schema)
   Style, materials, lighting, spatial layout - grounded in stage 2's
   references, not free-floating hallucination.
   |
   v
4. HERO IMAGE (comfyops-mcp, i2i/t2i)
   One reference-grounded still.
   |
   v
5. CAMERA-PATH WALKTHROUGH VIDEO (pluggable backend - see below)
   NOT independently-generated stills from "different angles" - see
   technical risk note below. A single video generation with camera-path
   conditioning maintains geometric consistency across frames the way
   independent still generations don't.
   |
   v
6. EXISTING PIPELINE (splat_generate operation="from_video")
   No new splat-side capability needed - the generated video feeds
   straight into the already-built ns-process-data -> ns-train ->
   ns-export chain exactly as a real phone video would.
```

**The load-bearing design insight: stages 1-5 are new, stage 6 is not.** Roughly 90% of the splat-generation infrastructure this needs already exists in the fleet (comfyops-mcp, plex-mcp, the already-built video pipeline) - `from_prompt` is a *composition* problem, not a new engine problem.

## Technical risk, flagged honestly

Multiple independently-generated still images of "the same room from different angles" have **no geometric consistency guarantee** - there's nothing forcing two separate diffusion generations to agree on where the fireplace is. Feed that into `ns-process-data images` and COLMAP's feature-matching/SfM step will likely fail outright, or worse, silently produce a corrupted pose estimate. This is why stage 5 specifies a **single video generation with camera-path conditioning**, not N independent stills - video diffusion models model temporal/spatial consistency across frames in a way independent generations don't. Needs to be verified against the actual chosen backend before committing to this design - flagged as unverified, not assumed.

## Stage 5 backend choice: comfyops vs. Veo 3 (2026-07-13, Sandra)

Worth naming honestly rather than defaulting past it: Google's Veo 3 is a genuinely stronger video model in general terms, and might handle multi-view consistency better than the fleet's local options. Real numbers before deciding anything:

- **Cost, verified against Google's Gemini API pricing table (checked 2026-07-13):** $0.40-$0.75/second depending on variant (Fast vs Standard), audio adds ~50%. An 8-second clip runs **$3.20-$6.00 per generation** on the direct API. This is not a rounding error - it reintroduces the exact "paid cloud API" cost problem this whole repo exists to route around, just relocated from World Labs to Google.
- **8-second cap per generation** is the sharper technical issue. A real photogrammetry-quality walkthrough usually wants far more coverage than 8 seconds. Chaining multiple generations is possible (Veo 3.1 has an "Extend" endpoint), but unless Extend preserves *rigid geometric continuity* - not just visual/stylistic continuity - across the cut, chaining could introduce a worse consistency break than a single comfyops i2v generation: the room's geometry could subtly drift between chained clips, which is exactly the failure mode that breaks COLMAP.
- **Whether Veo 3 is actually better at the thing that matters - rigid multi-view consistency usable for photogrammetry, not just "looks physically plausible" - is unverified in either direction.** Real evidence found: Veo 3 is marketed on physics/world consistency in general terms. No evidence found either way on photogrammetric reconstruction specifically, for Veo 3 or for the fleet's local models.

**Recommendation: make stage 5 pluggable, not a committed choice.** Same registry-style thinking as DeepSeek's `SplatBackend` suggestion, one layer up - a `VideoGenBackend` interface with comfyops as the default (free, local, fits the project's entire cost thesis, zero marginal cost per test) and Veo 3 as an opt-in paid alternative for comparison testing. Try comfyops first; if COLMAP genuinely can't reconstruct clean geometry from it, that's the moment to spend real money on one Veo 3 test generation - not the default starting point.

## Copyright/usage scope

Pulling stills from a copyrighted film (via plex-mcp, from Sandra's own library) as private, local, non-distributed creative/compositional reference is a materially different thing from reproducing or distributing copyrighted material. This design is scoped to **personal, local, non-published use** - generating a splat of your own home inspired by a film you own, kept on your own infrastructure. That scope should stay explicit if this ever gets built, not left implicit.

## Open questions before this could be scoped as a real build brief

1. Does the disambiguation stage ask a clarifying question, or pick a default and say what it picked? (Lean toward: ask once if genuinely ambiguous, default-and-announce otherwise - matches the fleet's general proactivity doctrine.)
2. Does comfyops-mcp's i2v actually maintain enough multi-view consistency for COLMAP to succeed, or does this need a different generation approach entirely (Veo 3 or otherwise)? Needs a real test, not an assumption.
3. Where does the Pydantic scene-spec schema live - splatmaker-mcp itself, or a shared fleet schema other creative-chain tools could reuse (worldlabs-adjacent chains, per the deep analysis doc's artistic chain)?
4. If Veo 3 is ever wired as an opt-in backend, does it go through a proper `veo-mcp`-style fleet server, or a direct API call from splatmaker-mcp itself? Fleet convention favors the former (per FLEET_INDEX's pattern of one server per external API surface) - check if one already exists before building a second.
