# Synapse v5: Product Requirements

> Written 2026-11-09 and reframed 2026-11-14, from the owner's direction of 2026-11-01, 2026-11-09 and 2026-11-14 and the v4 measurements. Everything v5 does not mention is inherited from the v4 PRD (`synapse-v4-PRD.md`).

## 0. Scope change from v4 (2026-11-14)

v4 was a lab for Malaysian KSSM Form 4 and 5 science. The owner, 2026-11-14:

> "for v5 we want to drop the narrative of kssm to general simple science simulation / environment + drop lab narrative into simulations / environments. this is for future dev of all generation (like engineering) not just form 4 and 5 science"

So v5:

- generates **simulations and environments** for any question, starting with general science and growing to other domains such as engineering (V5-D19);
- turns KSSM into the first optional **curriculum pack**: syllabus topics, textbook sources, Bahasa Melayu, the exam mirror, the Amali lab report (V5-D20);
- calls the top trust label **`source-verified`**, earned by a Kit model plus a quotation proved against any registered source corpus: a textbook, a standard or a reference handbook (V5-D21).

## 1. Problem

People learn science and engineering from descriptions of systems they never get to operate. v4 answers a question with a hands-on environment that is checked in a real browser and cited to a source. Three things stop it from being the product the owner pitches ("we are not a catalogue, we create anything you want"):

1. **Too slow for anything new.** A generated environment takes about 4 minutes (MEASURED). A student, or a judge, will not wait that long.
2. **The library acts like a catalogue.** A question near a stored environment can receive the stored environment, even when its twist is what made it worth asking. In v4, 16 of 60 library hits came from a topic or name match rather than the same question (MEASURED).
3. **It cannot hold a conversation.** An environment cannot be changed after it is made, and generated environments look less polished than the hand-built ones.

## 2. Users

- **Learner** (primary): anyone exploring a science idea, from secondary school upward, more often on a phone than a laptop. A curriculum pack (KSSM first) tailors topics, sources and language for a syllabus.
- **Teacher or lecturer**: shows an environment to a class (Present mode) and wants to trust what it says.
- **Later: engineering and other domains**: the same pipeline with domain parts, sources and packs (V5-D19).
- **Judge or visitor**: asks something unexpected and judges the product on what happens next.

## 3. Product thesis

> Ask anything. We build the experiment, then we tell you exactly how far it was checked.

ChatGPT and Gemini generate interactive answers quickly, and publish no correctness check for them (see `v5-design/docs/competitive-research.md`). Synapse's edge is the checking, the hands-on interaction and the cited sources. v5 keeps that edge and closes the speed and conversation gap.

## 4. Goals and targets

All targets are **TARGET** values. They are confirmed or revised after the V5-0 baseline and the V5-2 prototype. Times are measured at the client, from pressing Ask.

| # | Goal | Measure | Target |
|---|---|---|---|
| G1 | Every question ends in an environment made for it | Environments delivered per question asked (the twist and new sets) | 95 percent or more; the rest end with a simple environment, never a stand-in |
| G2 | Something useful appears immediately | First streamed words of the explanation | 2 s or less, p50 |
| G3 | The environment visibly forms | Title and Predict card visible | 6 s or less, p50 |
| G4 | The bench appears early | Forming picture of the bench visible | 15 s or less, p50 |
| G5 | The checked environment arrives | Live environment operable | 35 s or less p50, 60 s or less p90 |
| G6 | Changing an environment is quicker than making one | Live changed environment | 20 s or less, p50 |
| G7 | A repeated question is instant | Cache hit to live environment | 1 s or less |
| G8 | Generated environments look like one product | Owner's blind review of 10 generated environments against the Kit environments | 8 of 10 judged "same product" |
| G9 | Readable on a phone | Layout checks at 360 px: no colliding text, no label under the minimum size | 100 percent of delivered environments |
| G10 | Checks do not get weaker | L6 planted-defect detection rate | At or above v4's rate; reported, never assumed |
| G11 | Cost stays bounded | Mean spend per new environment | Measured in V5-2; cap enforced as in v4 |

## 5. Scope

v5 is organised as the owner's GenUI engine (`v5-design/docs/genui-engine.md`, V5-D08):

- the three levels of generative UI inside one reply;
- a Free writer that works from templates and components;
- the 13 accelerators;
- seven caching layers (`v5-design/docs/caching.md`).

In:

- Exact-question cache (V5-D01), template retrieval, warm-up while typing, a reviewed parts library and pre-built twists (V5-D12, V5-D13).
- Build Script writer reusing Kit parts and adding model-written parts (V5-D02, V5-D04).
- Lane computed from the script (V5-D03).
- Streaming and the forming environment (V5-D05).
- Faster verification with an unchanged or better detection rate (V5-D09).
- Layout checks (V5-D10).
- Bench-first page design.
- Change this environment (V5-D06).
- Deployment (V5-D11).

Carried from v4 unchanged:

- The Kit and its science models.
- The citations and the `source-verified` rule.
- The exact sandbox and CSP.
- The second reader (L4).
- Bahasa Melayu for library environments, Present mode, exam mirror, lab report, share links and offline export.
- The spend ledger and caps.

## 6. Non-goals

- Matching ChatGPT's general-purpose breadth (recipes, maps, budgets). Synapse is a science environment.
- Showing or running any model-written code before verification.
- Dropping the second reader or any browser check to save time.
- Accounts and a classroom management system (still single operator, v4 D-11).
- A learner study (v4 P8 remains its own phase).

## 7. Principles (added to v4's)

1. **Reuse before write.** If a Kit part can show it, the writer names the part instead of drawing it.
2. **Numbers are never model-written code.** The writer states formulas, and Synapse compiles them (V5-D04).
3. **Stop a doomed page early.** A check that can run on part of the reply runs as soon as that part arrives.
4. **The student is never idle.** Words, a prediction to make and a forming picture fill the wait.
5. **Per-part honesty.** Each part of an environment says what it earned ("Hooke's law: source checked. Mars twist: written by the model").

## 8. Dependencies and open items

See `v5-design/open-questions.md`. Q1 (where the code lives) blocks V5-0. Q2 (the prototype spend) blocks the V5-2 go/no-go.
