# Synapse v5

Ask any question and get an **Environment** built for it: an interactive simulation you work with your hands (drag, drop, pour, turn), checked in a real browser before you can touch it, with its source, the model that wrote it, and what was checked shown beside it. General science first; engineering and other domains next.

**Status (2026-11-14):** design written and the codebase set up. The code is still v4's, copied with full history, and v4's test suite is being re-run as the baseline. No v5 feature is built yet. See [`refdocs/STATUS.md`](refdocs/STATUS.md).

## What changes from v4

| v4 | v5 |
|---|---|
| A lab for Malaysian KSSM Form 4 and 5 science | General simulations and environments; KSSM becomes an optional curriculum pack |
| A stored lab answers a nearby question | The cache answers only the same question; anything new or twisted is generated |
| A Plan, then sometimes a whole Free page, about 4 minutes | An **Environment Blueprint** (hands-on by design), then one **Build Script** writer that reuses Kit parts when they help and writes from scratch when nothing fits |
| Nothing visible until every check passes | The Environment forms on screen as it is written (nothing operable until it passes its checks) |
| An Environment is final | "Change this Environment" by asking |
| Anthropic only | Free OpenRouter models first, up to three fallbacks, the paid Anthropic key last |
| `kit-verified` against a KSSM textbook | `source-verified` against any registered source |

Design: [`refdocs/v5-design/README.md`](refdocs/v5-design/README.md). It starts from the owner's GenUI plan ([`refdocs/v5-design/docs/genui-engine.md`](refdocs/v5-design/docs/genui-engine.md)).

## Requirements

- Python 3.13 and [uv](https://docs.astral.sh/uv)
- Node 24 and [pnpm](https://pnpm.io) 10
- Chromium for the verifier: `uv run playwright install chromium`
- No Docker and no database server: stores are SQLite

## Setup

```bash
uv sync
pnpm install
pnpm --filter @synapse/kit build
```

Then create `.env` by hand (it is never committed). Settings are documented in [`refdocs/guides/env_setup.md`](refdocs/guides/env_setup.md). Live use needs `OPENROUTER_API_KEY` (free models) and, for the paid fallback, `ANTHROPIC_API_KEY` with `LLM_MONTHLY_CAP_USD`.

## Usage

```bash
uv run uvicorn api.main:app --reload --port 8000
pnpm --filter web dev          # http://localhost:3000
```

**Do not expose the API publicly.** There is no auth yet; see the deploy gate in [`refdocs/guides/checklist.md`](refdocs/guides/checklist.md).

## Project layout

```
api/                 FastAPI: pipeline, verify (the trust path), evidence, llm seam and chains, routing
  prompts/           prompt packs, versioned files
web/                 Next.js: chat shell, forming Environment, sandbox host
packages/
  schema/            wire types (TypeScript), codegen to Pydantic
  kit/               micro-components and science models, bundle, manifest
eval/                question sets, hostile, planted-defect, speed, smoke
data/                stored Environments' sources, curriculum pack data, fixtures (no copyrighted text)
refdocs/             PRD, STATUS, v5 design, plans, execution, changelog, decisions, evidence; v4 history in refdocs/v4
.claude/             agents, commands, preflight, hooks
```

## Documentation

| Doc | What's in it |
|---|---|
| [`refdocs/STATUS.md`](refdocs/STATUS.md) | Where v5 actually is |
| [`refdocs/synapse-v5-PRD.md`](refdocs/synapse-v5-PRD.md) | Scope, goals, targets |
| [`refdocs/v5-design/`](refdocs/v5-design/README.md) | Roadmap, specs, open questions, backlog |
| [`refdocs/v5-design/decisions.md`](refdocs/v5-design/decisions.md) | The v5 decisions (V5-D01 onward); v4's D-01 to D-82 are in [`refdocs/changelog/DECISIONS.md`](refdocs/changelog/DECISIONS.md) |
| [`refdocs/changelog/CHANGELOG.md`](refdocs/changelog/CHANGELOG.md) | Session-by-session history |
| [`CLAUDE.md`](CLAUDE.md) | Operating brief for AI sessions |

## License

Not chosen yet.
