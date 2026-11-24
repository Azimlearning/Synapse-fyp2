# Synapse v5

> **Status, 2026-11-09: design documents only. Nothing is built.** Synapse v4 (`../Synapse-V4`) is the running product and stays frozen for the UTP CodeFest '26 Grand Finale on 14 November 2026. These documents record what v5 changes and why, so the build can start from a written plan (V4 rule 2: plan before you build).

## The idea in one paragraph

A student asks any science question, including a familiar one with a twist ("Hooke's law, but two springs in series on Mars"), and watches an environment form on screen within seconds. The student can then change it by asking ("now try it on the Moon"). Every environment is still checked in a real browser before it can be touched, and it shows what was checked.

v5 is the build that finishes the owner's own GenUI plan (`docs/genui-engine.md`):

- the three levels of generative UI inside one reply;
- a Free writer that works from templates and components;
- the 13 accelerators;
- layered caching.

It keeps v4's trust engine (the Kit, the verifier, the sandbox, the labels) and replaces how an environment is written:

- **One writer, not two.** The Plan step and the separate whole-page Free writer become one short reply in **Build Script**. It reuses audited Kit parts wherever they fit and adds model-written parts only for the twist.
- **Streamed.** The environment forms piece by piece while it is written, the way ChatGPT's Intelligent UI does. Nothing unchecked can be operated.
- **A cache, not a catalogue.** A stored environment is served only when the question is the same as one already answered. Anything new or twisted is generated.

The line to carry into every pitch: **"Ask anything. We build the experiment, then we tell you exactly how far it was checked."**

## Why v5

Measured on v4 (`../Synapse-V4/refdocs/evidence/2026-11-01-speed-visual-deploy-research.md`):

- A generated (Free) environment takes **about 4 minutes**: 220 s median of model calls, then about 15 to 20 s in the browser.
- 9 of the latest 11 Free runs wrote at least two whole pages.
- The owner reports the same 4 minutes on Opus and Sonnet, so a model switch is not the fix.
- Free environments bury the bench under text, have small, colliding labels on a phone, and look like a different product from the Kit environments.
- There is no way to change an environment after it is made.

## Reading order

| # | File | What it holds |
|---|---|---|
| 1 | [STATUS.md](../STATUS.md) | Where v5 stands; check this first |
| 2 | [docs/genui-engine.md](docs/genui-engine.md) | **Start here for the big picture:** how v5 finishes the owner's GenUI plan |
| 3 | [docs/how-to-start-v5.md](docs/how-to-start-v5.md) | From scratch or from v4? (From a copy of v4, step by step) |
| 4 | [docs/PRD.md](../synapse-v5-PRD.md) | What and why: goals, targets, scope, non-goals |
| 5 | [decisions.md](decisions.md) | The v5 decisions (V5-D01 onwards), each marked accepted, proposed or open |
| 6 | [roadmap.md](roadmap.md) | Build phases in dependency order, each with exit criteria |
| 7 | [docs/what-changes-from-v4.md](docs/what-changes-from-v4.md) | Kept, changed, dropped and new, part by part |
| 8 | [docs/architecture.md](docs/architecture.md) | The v5 pipeline from question to live environment |
| 9 | [docs/build-script.md](docs/build-script.md) | The format the writer replies in |
| 9a | [docs/blueprint.md](docs/blueprint.md) | The Environment Blueprint: the plan made before any generation, hands-on by design |
| 9b | [docs/model-chain.md](docs/model-chain.md) | Free OpenRouter models first, up to three fallbacks, the paid Anthropic key last |
| 10 | [docs/caching.md](docs/caching.md) | Seven caching layers; near-matches are templates, never answers |
| 11 | [docs/streaming-and-draft.md](docs/streaming-and-draft.md) | How the environment forms on screen while staying behind the trust line |
| 12 | [docs/verification.md](docs/verification.md) | Checks kept, checks added, and how they get faster without getting weaker |
| 13 | [docs/follow-ups.md](docs/follow-ups.md) | "Change this environment" |
| 14 | [docs/visual-design.md](docs/visual-design.md) | Bench first, one design language, phone legibility |
| 15 | [docs/speed-budget.md](docs/speed-budget.md) | The measured baseline, the targets, and each lever |
| 16 | [docs/evaluation-plan.md](docs/evaluation-plan.md) | Question sets, metrics and the prototype go/no-go gate, fixed before any run |
| 17 | [docs/deployment.md](docs/deployment.md) | Hosting and what the deploy gate needs |
| 18 | [docs/competitive-research.md](docs/competitive-research.md) | ChatGPT, Gemini and the wider GenUI field compared with Synapse |
| 19 | [docs/risks.md](docs/risks.md) | What could stop v5, and the response to each |
| 20 | [open-questions.md](open-questions.md) | Questions only the owner can answer |
| 21 | [improvements-backlog.md](improvements-backlog.md) | Every enhancement, including v4 items still open, sorted by when |
| 22 | [finale-plan.md](finale-plan.md) | What v4 shows on 14 November, and how v5 is presented (event context: stays out of the product repo) |
| 23 | [CLAUDE.md](../../CLAUDE.md) | The operating brief for build sessions |

## Rules for these documents

- No em dashes and no en dashes. Use commas, colons, new sentences, and "to" for ranges.
- Label every number: **MEASURED** (from v4 traces or a run), **ESTIMATE** (arithmetic, not yet run), or **TARGET** (what v5 aims for).
- A change in direction is a new entry in `decisions.md`, not a silent edit.
