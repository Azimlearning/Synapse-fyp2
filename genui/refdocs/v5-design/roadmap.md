# Synapse v5 roadmap

> Ordered by dependency, not by date (the owner's rule: time is not a variable). **Never build the second of anything until the first is green end to end.** Each phase needs a plan doc and an execution doc before code (v4 rule 2). Each ends with a changelog entry, a STATUS row and its exit check actually run.

```
V5-0 Foundations
  -> V5-1 Cache (exact only) + warm-up, and the free-first model chain
  -> V5-2 Blueprint and Build Script prototype  --(go/no-go)-->  V5-3 Blueprint then one writer in the pipeline
                                                   -> V5-4 Forming environment (streaming)
                                                   -> V5-5 Faster verification
                                                   -> V5-6 Visual design + layout checks
                                                   -> V5-7 Change this environment
                                                   -> V5-8 Parts library + pre-built twists + caches C5, C6
                                                   -> V5-9 Deployment
                                                   -> V5-10 Later
```

V5-4, V5-5 and V5-6 depend on V5-3 but not on each other.

## V5-0 Foundations

**Builds:**
- The v5 repository from a copy of v4 (`docs/how-to-start-v5.md`).
- A green baseline of v4's full suite.
- CI green on GitHub.
- Client timing marks and `eval/speed/report.py`.
- The question sets R, T, N, W and F written, approved and pinned (`docs/evaluation-plan.md`).
- The pruning commit.

**Exit:** the suite is green after pruning; CI is green; a speed report reproduces the v4 baseline from traces; the sets' hashes are committed.

**Needs:** Q1.

## V5-1 Cache, warm-up and the model chain

**Builds:**
- The free-first model chain (`docs/model-chain.md`, V5-D22): the OpenRouter provider, per-purpose chains, the quota check, pacing, the paid Anthropic last resort.
- `_from_library` serves only the question key (V5-D01).
- Topic and name matching become `nearest_labs()` for templates (C2).
- Route and retrieval run while the student types, locally (C7). **Moved to V5-1c, 2026-11-14:** it needs a web change and a new endpoint, so V5-1 stays small.

**Exit:** set R served in 1 s or less with no model call; a twist from set T is never served a stored environment (tested); a live call goes through each chain step in a test with a mock transport; one live free call made with the owner's OpenRouter key; STATUS updated.

## V5-2 Blueprint and Build Script prototype, and the go/no-go gate

**Builds** (the automated tests use the fake model; every measurement is live, V5-D17):
- The Blueprint: schema in `packages/schema`, the prompt pack, the deterministic plan checks (every changed variable is hands-on, at least one drag or drop), and expected behaviours compiled into browser tests (`docs/blueprint.md`).
- The Build Script parser and unit splitter.
- The validator, with v4's PLAN rules moved in.
- The formula compiler (JavaScript) and evaluator (Python).
- The assembler on `free_house.py`.
- Pattern templates.
- The prompt pack `build_script.v1.md`, with Kit pack and `@@BASE` retrieval.
- Fixture scripts for 5 twists that pass every existing check.

**Then:** the live gate on 3 twists, on free models (`docs/evaluation-plan.md` section 3; `ALLOW_PAID_FALLBACK=false` unless the owner sets a budget).

**Exit:** the gate's go criteria met, or a recorded no-go with a revised spec.

**Needs:** Q14 (OpenRouter key); Q2 only if a paid comparison is wanted.

## V5-3 Blueprint then one writer in the pipeline

**Builds:**
- `_write_environment` replaces the plan step and `_free_page`.
- Explain and write in parallel.
- Early stop on the first failed unit.
- Lane computed (V5-D03).
- Per-part badges.
- The Build Script stored with each environment.
- The simple-page last step kept.

**Exit:** sets T, N and W on fakes pass end to end; a small paid run of the T set (stated amount) shows environments delivered of 95 percent or more and live-environment p50 within 60 s. V5-4 and V5-5 bring it to target.

## V5-4 Forming environment (streaming)

**Builds:**
- Draft events in `packages/schema` and codegen.
- The SVG sanitiser (server and host).
- `FormingLab` in the web app.
- Predict answerable while waiting.

**Exit:** the client marks meet the title and picture targets on the T set; the smoke test proves nothing in the draft can be operated and no model script runs before the `environment` event; V5-D05 wording accepted.

**Needs:** Q3.

## V5-5 Faster verification

**Builds:**
- The virtual clock.
- A warm browser.
- Reader and browser in parallel.
- The verification result cache (C6).

**Exit:** L6 rate at or above v4's, no new false positives, hostile 20 of 20, and browser time per environment reported against the baseline.

## V5-6 Visual design and layout checks

**Builds:**
- The bench-first house frame shared by Kit and generated environments.
- Subject backdrops.
- Vendored fonts (Kit relock, 0.2.0).
- Layout checks.
- A full visual review including motion, dragging and dark mode.

**Exit:** the acceptance in `docs/visual-design.md` section 4.
**Added 2026-11-14 (V5-D23):** the fill check calibrated on the stored Environments, with its detection rate on planted empty-space defects reported; Kit scenes that fail (the Wave speed picture) fixed with a Kit relock; the owner's 1920 px screenshot rechecked.

## V5-7 Change this environment

**Builds:**
- `parent_env_id` and `state` on `/ask`.
- The patch merge.
- `@@TWISTS` chips.
- The parent breadcrumb.

**Exit:** set F meets its targets (`docs/follow-ups.md` section 6).

## V5-8 Parts library, pre-built twists, and the remaining caches

**Builds:**
- C3 with its lifecycle and review queue.
- C4 batch generation of likely twists (stated cost, owner's amount).
- C5 prompt caching turned on after one measured run.

**Exit:** each layer's measure reported (`docs/caching.md`); no part offered before review.

## V5-9 Deployment

**Builds:**
- Docker build in CI.
- The library inside the image.
- An access code.
- A no-network verification container.
- The chosen host.

**Exit:** the deploy gate met and recorded, or a recorded time-boxed waiver (V5-D11); a phone rehearsal on mobile data.

**Needs:** Q4, Q5.

## V5-10 Later

- An interactive Kit-only draft (V5-D05b).
- A design reader.
- A learner note fed to the writer (gap G2).
- Remembered environments in spaced practice (G8).
- The writer choosing the pattern template (G1).
- Malay for generated environments.
- The full measurement (`docs/evaluation-plan.md` section 4).
- v4's open items in `improvements-backlog.md`.
