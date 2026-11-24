# Synapse v5: Architecture

> v4's pipeline is in `../../Synapse-V4/refdocs/guides/generation_pipeline.md`. This is the v5 replacement for its stages 2 and 5 to 9; the rest is kept.

## 1. The flow

Times are **TARGET** values (`speed-budget.md`).

```
Student presses Ask
  |
  |-- 1. Intake: refuse obvious prompt injection                         (ms)
  |-- 2. Cache: the same question asked before? -> serve it, done         (< 1 s)
  |-- 3. Route: topic, subject, the nearest stored environments (starting material)  (local, ms; model only if unsure)
  |
  |-- 4. Explain -------------------- streams words to the chat           (first words < 2 s)
  |-- 4b. Blueprint ------------------ starts at the same time as Explain (docs/blueprint.md)
  |       |  concept, objects to touch and how, scene, science source, expected behaviour, optional assists
  |       |  streams into the forming environment; deterministic plan checks (every changed variable is hands-on)
  |-- 5. Write (Build Script) --------- carries out the plan; assists optional, from scratch when nothing fits
  |       |  each completed section is parsed, validated and checked AS IT ARRIVES
  |       |  - text sections      -> forming environment shows title, Try this, Predict, Steps   (< 6 s)
  |       |  - PARTS, FORMULAS    -> checked against the Kit manifest and the formula rules
  |       |  - DRAWING            -> sanitised, shown as an inert picture  (< 15 s)
  |       |  - SCRIPT             -> scanned, never run here
  |       |  a failed check STOPS the reply and starts one retry told the reason
  |
  |-- 6. Assemble: Kit calls + compiled formulas + model drawing script into the house frame
  |-- 7. Check, in parallel:
  |       - the second reader (L4) reads words, formulas and drawing labels
  |       - the browser run: controls, handles, drags, layout, provenance audit,
  |         formula readouts against the Python evaluation, Kit models against their references
  |-- 8. Ground: Kit models with citations proved against the corpus
  |-- 9. Mint, store (with the Build Script source), deliver
  |
  Live environment replaces the forming environment                                        (< 35 s p50)
```

The fallback is v4's, kept. When the first script fails twice, the simple-page last step runs, up to three times, each told why the last was refused. Every question ends in an environment (v4 D-80).

## 2. What changes in the code (v4 paths)

| v4 file | Role in v5 |
|---|---|
| `api/pipeline/run.py` | The orchestrator. `_from_library` keeps only the question hit. The plan step becomes the Blueprint (V5-D18). Compose assembly and `_free_page` give way to one `_write_environment` that consumes a stream of Build Script units |
| `api/pipeline/library.py` | Keeps `canonical_question`. Topic and name matching become `nearest_labs()`, which returns starting material, not answers |
| `api/pipeline/free_house.py` | Becomes the Build Script assembler. It already turns `@@` sections into the house frame (v4 D-81) |
| `api/pipeline/plan_checks.py` | Rules that apply to PARTS and FORMULAS move into the Build Script validator (units, domains, ranges, constants, PLAN-020) |
| `api/pipeline/assemble.py` | Its Kit-call writer is reused for PARTS |
| `api/verify/*` | Kept. Gains the formula reference check, layout checks, the virtual clock and a warm browser |
| `api/pipeline/wording.py` | Kept. Reads the script by sections, so the length limit applies to what a reader can take, not to the page as a whole |
| `packages/schema/src/events.ts` | Gains the draft events (`streaming-and-draft.md`) |
| `web/components/` | Gains `FormingLab`. `PeekSkeleton` and `BuildLog` give way to it, and the code view moves behind a disclosure |
| `api/verify/store.py` | Gains the Build Script source per environment, and the parent environment for a changed environment |

## 3. Lanes, computed (V5-D03)

| What the validated script contains | Lane | Highest label it can earn |
|---|---|---|
| Only Kit parts and Kit scenes; every readout fed by a Kit science model; no SCRIPT section | Compose | `source-verified` (with citations), else `model-checked` |
| Any FORMULAS line, model-written DRAWING or SCRIPT | Free | `model-checked`, shown as model-written (v4 hard constraint 3) |
| Same question as before | Cache | Whatever the stored environment earned |

Within a Free environment, each part carries its own badge (`verification.md` section 6), so a Kit science model inside a twist still shows "source checked".

## 4. Parallel and early work

| What | v4 | v5 |
|---|---|---|
| Explain and write | Explain, then Plan, then Free, in sequence | Explain and Write start together after Route |
| Checks on the reply | After the whole reply | Per section while streaming. Stop at the first failure |
| Second reader and browser | Reader, then browser | Together. Either refusing refuses the environment |
| Browser start | A new Chromium per check | A warm browser held by the worker, a fresh context per environment |
| Starting material | None for Free | The nearest stored environments' Build Script, so the writer copies what fits |

## 5. Data stored per environment

| Field | Why |
|---|---|
| HTML, hash, label, lane, citations, checked layers (as v4) | Delivery gate |
| `lab_script` (the validated source) | Change this environment, audits, gap analysis |
| `parent_env_id` | A changed environment knows what it changed |
| `parts_provenance` | Per-part badges |
| `timings` (stage marks) | Speed measurement |

## 6. Failure handling

| Failure | Response |
|---|---|
| A section fails validation while streaming | Stop the reply. Retry once with the reason in our checker's words |
| The retry fails | Simple-page last step (v4 D-80), up to three attempts |
| The reader refuses | As v4: one retry with its issues, then the last step |
| The browser refuses | As v4: one retry with the failed check, then the last step |
| Spend cap reached | As v4: refuse before sending, say so plainly |
| Everything fails | The student sees the explanation and a clear "no environment this time" note (v4 behaviour, should be rare) |
