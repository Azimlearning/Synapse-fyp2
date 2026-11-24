# What changes from v4

> v4 paths are relative to `../../Synapse-V4/`.

## Kept as it is

| Part | v4 location | Why it stays |
|---|---|---|
| The Kit: 65 manifest entries, 26 apparatus parts, about 35 cited science models | `packages/kit/` | It is v4's best asset. v5 uses it more, not less |
| The verifier: scan, postprocess, provenance audit, browser run, drags, independent references | `api/verify/` | The trust engine is the product's edge |
| Mint, store, delivery gate, browser re-hash | `api/verify/mint.py`, `store.py`, `web/components/EnvironmentFrame` | Hard constraint 1 |
| Exact sandbox (`allow-scripts` only) and the named-origin CSP | `api/verify/postprocess.py` | Hard constraint 2 |
| Citations and the `source-verified` rule | `api/pipeline/grounding.py`, `data/citations/` | Hard constraint 4 |
| The second reader (L4) | `api/pipeline/wording.py`, `api/prompts/verifier_l4*` | It is the only content check a model-written part gets |
| Spend ledger, caps, fakes by default | `api/llm/` | Hard constraint 8 |
| Explanation streamed first | `api/prompts/explainer.v3.md` | Already gives words in about 1 to 3 s |
| Teaching extras: hints, predict, concept check, exam mirror, lab report, probes | Kit pedagogy parts, `web/components/` | Unaffected |
| Bahasa Melayu for library environments, Present mode, share links, offline export, chapter packs | various | Unaffected |
| "Every question ends with an environment", simple-page last step | `api/pipeline/run.py` `_last_resort` | Owner's rule (v4 D-80) |

## Changed

| Part | v4 | v5 | Decision |
|---|---|---|---|
| Library | Answers by the same question, by a confident topic or by a named environment | Answers only the same question (normalised words). A twist always generates. Stored environments become **starting material** for the writer | V5-D01 |
| Writing an environment | Two model steps: a Plan (JSON), then, when Free leads, a whole page | One **Build Script** reply that names Kit parts and adds model-written parts for the twist | V5-D02 |
| Lane | Chosen before writing (`LANE_PREFERENCE`, planner `fit`) | Computed from what the script contains | V5-D03 |
| Who writes the maths | The Free page's own JavaScript computes the readouts | The writer states formulas, Synapse compiles them to JavaScript, and Python evaluates the same formulas as a reference | V5-D04 |
| What the student sees while waiting | Explanation, a stage log, the page's code as text | Explanation, then the environment forming: title, a Predict card to answer, Steps, the parts, then an inert picture of the bench | V5-D05 |
| When checks run | After the whole page is written (a too-long page is found after 100 to 170 s) | Each section is checked as it arrives, and the reply is stopped at the first failure | V5-D02, `verification.md` |
| Browser check timing | A fixed 10 s of pressing controls | A virtual clock, accepted only if L6 holds; a warm browser; the reader runs alongside the browser run | V5-D09 |
| Generated page layout | Text cards above the bench (bench at 575 px on desktop, 1,162 to 1,242 px on a phone) | Bench first, after the title and Try this | `visual-design.md` |
| Drawing rules | Light bench backgrounds, no size rules | Themed backdrops, minimum label size at 360 px, Kit look | `visual-design.md` |
| Layout checking | None | Collisions, overflow and minimum text size checked in the browser | V5-D10 |
| Model tier | `GENERATION_TIER=heavy` (Opus) set for demo day | Chosen by measurement on the twist set; standard is the default | V5-D07 |
| What is stored per environment | HTML and metadata | Also the Build Script source, so an environment can be changed | V5-D06 |

## Dropped

| Part | Why |
|---|---|
| The planner's separate call before Free | One writer replaces it. Its checks (PLAN-001 to PLAN-023) move into the Build Script validator where they apply |
| Topic and name library hits | V5-D01 |
| `LANE_PREFERENCE` | The lane is computed |
| The code view as the main "watch it build" feature | The forming environment replaces it. The code view stays behind a disclosure for the curious and for judges |

## New

| Part | Spec |
|---|---|
| Build Script format, parser, validator and assembler | `build-script.md` |
| Formula compiler (to JavaScript) and evaluator (in Python) | `build-script.md` section 5, `verification.md` |
| Streaming draft events (typed in `packages/schema`) and the forming environment view | `streaming-and-draft.md` |
| Per-part provenance badges | `verification.md` section 6 |
| Layout checks | `verification.md` section 4 |
| Change this environment (patch replies, merge, full re-check) | `follow-ups.md` |
| Suggested twists under each environment ("Try it on the Moon") | `follow-ups.md` section 4 |
| Client-side timing (time to first words, title, bench, live environment) | `speed-budget.md` |

## Added 2026-11-14

| Part | v4 | v5 |
|---|---|---|
| Empty space | Not checked. The stored Wave speed Environment shows a small picture in a wide bench card and an empty area under it at 1920 px | Blueprint scene rule, a reflowing house frame, scaled apparatus and a browser fill check on every Environment, Kit or generated (V5-D23) |
