# Hosted demo

Two Vercel projects show Synapse without its Python backends:

| Project | Root | What it is |
|---|---|---|
| [synapse-fyp2-demo](https://synapse-fyp2-demo.vercel.app) | `web/` | The Synapse app: chat, Studio, notes, knowledge graph, labs, and the Simulations tab |
| [synapse-fyp2-simulations](https://synapse-fyp2-simulations.vercel.app) | `genui/web/` | The simulation engine's app, embedded by the first one |

**What is real and what is replayed.** The interface is the real app, built with `NEXT_PUBLIC_DEMO=1`. Its backend is a
Next.js route (`web/app/demo-api/[...path]/route.ts` and `genui/web/app/demo-api/[...path]/route.ts`) that replays responses
recorded from the real servers on the 16-paper corpus: every chat turn was answered by the live model once, and every
simulation is a stored library Environment. No model is called on Vercel and nothing a visitor does is stored. A question that was
not recorded gets a message saying so; uploads and other writes are refused with a clear reason.

Why not the real backend on Vercel: the corpus vault alone is 430 MB (over the function size limit), the stores are SQLite files
that need a writable disk, the simulation verifier needs Chromium, and the APIs have no authentication, so a public deployment
could spend the API credits without limit.

## Re-recording

```bash
# 1. The GraphRAG API on a copy of the corpus (quiz answers record learner events), in live mode for the chat turns
cp -r data/viva-demo data/demo-record
ARCANA_DATA_DIR=data/demo-record uv run uvicorn api.main:app --port 8000
uv run python demo/record/record_graphrag.py          # views (free), then each question in CHAT once (paid)

# 2. The simulation API in library mode (no model call)
cd genui && SYNAPSE_LLM_MODE=fake PUBLIC_ORIGIN=http://localhost:3001 uv run uvicorn api.main:app --port 8001
uv run python demo/record/record_simulations.py
```

Recordings go to `web/demo-data/graphrag/` and `genui/web/demo-data/`, which are committed.

## Building and deploying

```powershell
# Local check (a separate build folder, so start-synapse.ps1's build is untouched)
$env:NEXT_PUBLIC_DEMO="1"; $env:NEXT_PUBLIC_API_BASE_URL="/demo-api"; $env:NEXT_DIST_DIR=".next-demo"
pnpm --filter web build                                  # from the repo root, with NEXT_PUBLIC_SIMULATIONS_URL set
cd genui; pnpm --filter web exec next build --webpack   # from genui/

# Deploy: both projects are connected to this GitHub repository (branch main), so a push to main deploys both.
# Project settings hold the env vars and the root directories: web/ and genui/web/.
```

`.vercelignore` keeps the Python backends and corpus data out of both builds.
