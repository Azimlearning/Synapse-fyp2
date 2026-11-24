# The GenUI engine: how v5 finishes the owner's generative UI plan

> v5 is meant to be the biggest step Synapse has taken. It gets there by finishing a design that already exists, not by inventing a new one. The owner's GenUI work set the direction in three documents:
> - `../../research/generative-ui-research-2026-07-06.md`: the three levels, the escalation ladder, gaps G1 to G8.
> - `../../Synapse-V4/refdocs/brainstorm-2026-10-16.md`, Amendment A1: three lanes over a Kit, prompt packs, 13 accelerators, "template, fences, checking, save, reuse".
> - v2's restricted expression grammar and Arcana v2's lifecycle.
>
> v4 built the trust half of that plan. v5 builds the generative half.

## 1. The three levels, in one reply

The research's key insight was that the levels are "not competing philosophies but tiers of one system". v4 runs them as separate lanes with separate model calls. v5 puts all three inside one Build Script reply (`build-script.md`), so escalation happens per part, not per question:

| Level (owner's taxonomy) | In v5 | Speed and safety | Example |
|---|---|---|---|
| **Level 1**: pick a pre-built component and fill its props | `@@PARTS` lines naming Kit parts; a cache hit; a stored environment as `@@BASE` | Fastest, audited, can earn `source-verified` | `g = planetGravity {"planet": "mars"}` |
| **Level 2**: a declarative UI description | `@@CONTROLS`, `@@READOUTS`, `@@FORMULAS`, the text sections. This is v2's restricted expression grammar, back as a first-class format | Streams, no code-safety surface, independently recomputed | `k_total = 1 / (1/k1 + 1/k2) [N/m]` |
| **Level 3**: the model writes code | `@@DRAWING` and `@@SCRIPT`, for drawing and handles only | Most expressive, most checked, labelled model-written | A bespoke series-spring drawing |

Levels 1 and 2 assist; they are never required (V5-D16). When nothing fits, the whole environment is Level 3, written from scratch after the Blueprint (V5-D18). Most questions should still need little Level 3. The more the Kit and the parts library grow, the less is written from scratch, so each environment gets faster and better checked than the last one on that topic.

This is the same shape OpenAI ships: a catalogue of components plus an escape hatch for model-written code (`competitive-research.md`). Synapse adds what nobody publishes: independent recomputation, source citationsook citations and a browser run on every environment.

## 2. "The Free lane assistant with templates and components"

The owner's phrase, as v5 reads it. **This interpretation should be confirmed (open question Q11).**

The Free writer stops starting from a blank page. It works like an assistant at a bench that is already set up:

- **Templates** it starts from:
  - the house frame (v4 D-81);
  - one **pattern template** per kind of environment (simulation, virtual experiment, explorable diagram, data plot, drag-and-drop sort, process stepper, Amali bench, from A1.4's pattern packs);
  - the **nearest stored environments** as `@@BASE`, so a twist edits a working environment rather than rebuilding it (A1.5 accelerators 2 and 3).
- **Components** it builds with:
  - the Kit (65 entries, 26 apparatus parts, about 35 cited science models);
  - and a new **parts library** of generated parts that passed verification and review (`caching.md` layer C3), so a good black hole or pendulum drawing is written once and reused.

## 3. The 13 accelerators from Amendment A1.5

| # | Accelerator | v4 state | v5 plan |
|---|---|---|---|
| 1 | Library lookup | Built (D-42), later narrowed | Cache layer C1, exact only (V5-D01) |
| 2 | Template instantiate | Partly: library Plans and the house frame | `@@BASE` plus pattern templates (section 2) |
| 3 | Edit, not regenerate | Not built | Change this environment and twist-from-base (`follow-ups.md`). MAIC-UI reports full regeneration at 200 to 600 s and diff edits in under 10 s |
| 4 | Kit retrieval (only relevant docs in the prompt) | Built (Kit pack) | Kept; the parts library joins it |
| 5 | Model tiering | Built | Chosen by measurement (V5-D07) |
| 6 | Prompt caching | Built, off | Turn on after one measured run (layer C5) |
| 7 | Skeleton first | Partly: a loading card from the Plan | The forming environment (`streaming-and-draft.md`) |
| 8 | Early gates | Partly: cheap checks, but after the whole page | Per-unit checks while streaming, stop at the first failure |
| 9 | Deterministic repair | Built (post-processor rules) | Kept; a failure class seen three times becomes a rule or a Kit guard |
| 10 | Output budget | Built (`max_tokens`) | Per pattern template; Build Script is short by design |
| 11 | Overnight fill | Not built | Pre-built twists (layer C4), owner-approved spend |
| 12 | Question canonicalisation | Built | Kept for layer C1 |
| 13 | Per-request budget and degrade | Built | Kept |

## 4. The research's open gaps, and what v5 does about each

| Gap (research section 7) | v5 response |
|---|---|
| G1 When and what form (text, chart or environment) | Not in v5's core: the owner's rule is an environment for every question (v4 D-80). Backlog: let the writer choose the environment's pattern template, which is the form decision inside the environment |
| G2 Generation driven by the learner, not just the question | The device-local progress and misconception probe feed the writer a short "this student" note (backlog, after V5-7) |
| G3 Faithfulness of generated interactives | v5's core claim: Kit models with citations, formulas recomputed in Python, the second reader, per-part badges |
| G4 Latency | v5's first target: one short writer, streaming, early stops, caching (`speed-budget.md`) |
| G5 Outcome evaluation, not preference | v4 P8's learner study, unchanged; v5's environments make it cheaper to run |
| G6 Opaque process | The forming environment shows each part as it is chosen, and the badges show what was checked |
| G7 Accessibility by construction | Synapse, not the model, writes every control, readout and label element; the keyboard fallback is generated from the controls |
| G8 Remembered interactives | Every environment is stored with its Build Script; spaced practice re-summons the same environment, and change-this-environment continues it (backlog) |

## 5. Why this is the biggest step

| v1 to v4 | v5 |
|---|---|
| Each build solved one part and dropped another (brainstorm, finding 2): v1 pedagogy, v2 safe formulas, v3 free generation, v4 verification | v5 keeps v4's verification and brings back v2's formulas and v3's free generation in one format |
| Generating meant waiting minutes | The environment forms in seconds and is live in well under a minute (TARGET) |
| An environment was final | An environment is a conversation: twist it, change it, come back to it |
| The Kit grew only by hand | The parts library grows from every verified generation, with review before promotion |
