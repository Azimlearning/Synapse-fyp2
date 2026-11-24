# Synapse (FYP2)

**A GraphRAG-powered generative UI platform for interactive learning.** Drop in your own papers and notes, ask a
question, and get a cited answer, study tools built from your own documents, and, for science questions, an
interactive simulation that was tested in a real browser before you could touch it.

**Live demo: [synapse-fyp2-demo.vercel.app](https://synapse-fyp2-demo.vercel.app)** (simulations on their own:
[synapse-fyp2-simulations.vercel.app](https://synapse-fyp2-simulations.vercel.app)). The demo is the real interface replaying
answers recorded from the real system on its 16 research papers; no model runs there, so it answers the recorded questions and
every Studio tool, not new ones. See [`demo/README.md`](demo/README.md).

Final Year Project 2, Bachelor of Computer Science (Hons), Universiti Teknologi PETRONAS.
Fakhrul Azim Bin Ahmed Mardzukie. Supervisor: Dr Mazeyanti Bt M Ariffin. Co-supervisor: AP Dr Noreen Izza Bt Arshad.

> **Where this repository sits.** This is the code of the FYP2 submission. It started as
> [Arcana v2](https://github.com/Azimlearning/Arcana-v2) (kept as it was before Synapse, with its history) and grew
> into Synapse by adding the simulation engine in [`genui/`](genui/) and a new interface. The full history of
> Arcana v2 is in this repository's git log. The paper, talks, viva slides and achievements are in the
> [FYP showcase repository](https://github.com/Azimlearning/Arcana-Final-Year-Project-UTP).

## What it is

Synapse is one product made of two engines that share one idea: *what the system can retrieve decides what it is
allowed to show.*

| Engine | Where | What it does |
|---|---|---|
| **GraphRAG engine** | `api/`, `web/` (ports 8000 and 3000) | Turns documents into a knowledge graph plus a vector index, fuses graph, dense and sparse retrieval by rank, and answers with citations that are word-for-word quotes of stored passages. Runs the agents, the Studio and the adaptive layout |
| **Simulation engine** | `genui/` (ports 8001 and 3001) | Turns a question into an interactive Environment: a library of stored, tested simulations answers repeat questions with no model call, and anything new is written by a model, then refused or passed by an automated test gate |

The web app shows both: a chat with the Studio and knowledge graph on one side, and a **Simulations** tab and
drawer that opens the simulation engine inside the same window.

## What it does

- **Cited answers.** Every sentence carries a citation that is a verbatim quote with its paper and page. A question
  the documents do not cover gets *"No evidence found in your documents"*, not an answer from general knowledge.
- **Agents.** Orchestrator, Research, Graph and Fact Checker agents with typed tools. They call each other only through
  `route_to_agent`, within hop and token budgets, and the interface shows which ran, with tokens and time.
- **Adaptive interface.** The server chooses the layout and admits a component (comparison grid, concept map, search
  path, draft, study set) only when the retrieved evidence satisfies that component's written precondition.
- **Studio (14 tools).** Among them: quiz, flashcards, blurting, Cornell notes, Socratic questions, document brief,
  cheat sheet, literature review, abstract, audio-overview script, review schedule and learning insights. The
  flashcard-style tools are built from the documents with no model call, and answers are checked by the server.
- **Knowledge graph.** The concept graph of the corpus, with concept pages and cited definitions you can ask about in chat.
- **Simulations.** A drag-and-drop Environment for a science question, shown with its trust label and what was
  checked. A stored library answers a repeated question in about 0.15 s.
- **Test gate.** Generated simulations go through checks that run in a browser with no network, and a failed check
  means the simulation is not shown.

## Findings

These are the measured results, with limits stated in [`refdocs/evidence/`](refdocs/evidence/README.md) and
[`genui/refdocs/evidence/`](genui/refdocs/evidence/). They are honest ones, and not all are positive.

- Hybrid retrieval with the graph signal is **not shown to beat dense retrieval alone** on the 16-paper corpus
  (38 questions, no pair of methods significantly different).
- The grounding constraint holds with a real model: every quote verbatim, and an unanswerable control question refused.
- A trained re-ranker was built, measured and **not shown to help**, so it was dropped.
- The test gate refused 219 of 224 planted faults, raised no false alarm on 30 correct simulations and blocked all
  20 hostile inputs. The faults were written by the author, so this is a baseline for catching regressions, not an
  unbiased score.
- 31 library simulations pass 59 of 59 browser checks. 13 of 14 new questions got a simulation, at about 5.7 US cents each.
- Not done: no teacher has reviewed the simulations and no learner study has been run. Brand-new simulations are still slow.

## Run it

Requirements: Node 20+ and pnpm 9.12 for the GraphRAG engine; Python 3.12 or 3.13 with [uv](https://docs.astral.sh/uv);
the simulation engine in `genui/` uses Python 3.13, Node 24 and pnpm 10, and Chromium for its verifier
(`uv run playwright install chromium`). No Docker and no database server: stores are SQLite.

With no API keys everything runs on deterministic fakes at no cost (`ARCANA_LLM_MODE=fake`, the default).

```bash
cp .env.example .env          # fill in values only for live mode; never commit .env
uv sync && pnpm install       # GraphRAG engine
cd genui && uv sync && pnpm install && pnpm --filter @synapse/kit build && cd ..
```

Start all four servers on Windows, each in its own window (GraphRAG API on 8000, app on 3000, simulation API on 8001,
simulation app on 3001; open <http://localhost:3000>):

```powershell
powershell -ExecutionPolicy Bypass -File .\start-synapse.ps1
powershell -ExecutionPolicy Bypass -File .\stop-synapse.ps1
```

Or run the GraphRAG engine by hand:

```bash
uv run uvicorn api.main:app --reload   # API, fakes by default
pnpm --filter web dev                  # http://localhost:3000
uv run pytest -q                       # backend tests
pnpm -r test                           # web and schema tests
```

A live run needs `LLM_MONTHLY_CAP_USD` set to a positive number (every paid call is booked and refused before
sending if it would pass it) and the keys in [`refdocs/guides/env_setup.md`](refdocs/guides/env_setup.md). Live
simulations use free OpenRouter models first, with a paid fallback only when a cap is set.

**Do not expose either API publicly.** There is no authentication, and the limits that exist are in-process.

A hand-test script with prompts, expected output and expected visuals for every tool is in
[`refdocs/guides/manual-testing.md`](refdocs/guides/manual-testing.md). A PDF uploaded in the app gets answers,
comparisons and writing at once; the learning tools need a corpus built first (see that guide).

## Project layout

```
api/              FastAPI backend: core, llm, stores, ingestion, retrieval, agents, genui, engines, labs
web/              Next.js app: shell, registry, catalog components, Studio, graph, Simulations tab
packages/schema/  wire types, the single source of truth, generated into Python
eval/             questions, corpus manifest, gold set, ablation runner, audit, mutation suite
refdocs/          PRD, status, decisions, plans, execution docs, evidence, guides
genui/            the simulation engine (its own api/, web/, Kit of tested components, eval/ and refdocs/)
start-synapse.ps1 starts the four servers; stop-synapse.ps1 stops them
```

## Documentation

| Doc | What is in it |
|---|---|
| [`refdocs/STATUS.md`](refdocs/STATUS.md) | Where the GraphRAG engine's build is, phase by phase |
| [`genui/refdocs/STATUS.md`](genui/refdocs/STATUS.md) | Where the simulation engine's build is |
| [`refdocs/arcana-v2-PRD.md`](refdocs/arcana-v2-PRD.md) | Scope, architecture, roadmap and decision log of the GraphRAG engine |
| [`genui/refdocs/v5-design/README.md`](genui/refdocs/v5-design/README.md) | Design of the simulation engine |
| [`refdocs/evidence/README.md`](refdocs/evidence/README.md) | Every measurement, with its limits |
| [`refdocs/changelog/CHANGELOG.md`](refdocs/changelog/CHANGELOG.md) | Session-by-session history |
| [`refdocs/changelog/DECISIONS.md`](refdocs/changelog/DECISIONS.md) | Why things are the way they are |
| [`CLAUDE.md`](CLAUDE.md) | Operating brief for AI sessions on this repository |

## Lineage

| Repository | What it is |
|---|---|
| [Arcana](https://github.com/Azimlearning/Arcana) | v1, frozen at tag `v1.0`: the system the MCAIT 2026 paper describes |
| [Arcana-v2](https://github.com/Azimlearning/Arcana-v2) | The GraphRAG rebuild, as it was before Synapse (this repository continues it) |
| [Synapse-v4](https://github.com/Azimlearning/Synapse-v4) and [synapse-hackastone](https://github.com/Azimlearning/synapse-hackastone) | The simulation engine's earlier versions, used in the hackAstone and CodeFest competitions |
| [Arcana-Final-Year-Project-UTP](https://github.com/Azimlearning/Arcana-Final-Year-Project-UTP) | FYP showcase: paper, talks, viva and achievements |

## Publication

F. A. B. Ahmed Mardzukie, "Graph-Grounded Generative User Interfaces for Learning: Retrieval Structure Determines
Interface Expressiveness," in *Proc. 6th International Multi-Conference on Artificial Intelligence Technology
(MCAIT 2026)*, Madinah, Saudi Arabia, Nov. 2026. Accepted and presented on 5 November 2026. The paper describes
Arcana v1; findings marked "after the paper" in the talk come from the evidence in this repository and were not
peer reviewed.
