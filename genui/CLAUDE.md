# Synapse v5: Claude Context

> Read this file at the start of every session, then walk `.claude/memory/preflight.md`, the six-question gate.
> Synapse v5 turns any question, general science first and other domains such as engineering later, into a verified, interactive **Environment**: a simulation the user works by hand (drag and drop first). It is planned as an Environment Blueprint, written as an Environment Build Script over a vetted micro-component Kit (which assists but never constrains), checked in a real browser, and labelled for what it survived.
> v5 is built from a copy of v4 (git history kept; v4 is the read-only `v4` remote). The PRD is the source of truth; this file is the short operating brief; preflight is the gate.

---

## Order of authority (when docs conflict, surface it; don't resolve silently)

0. `refdocs/STATUS.md`: **where v5 is right now.** Check first, every session.
1. `refdocs/synapse-v5-PRD.md`: **what and why** for v5.
2. `refdocs/v5-design/decisions.md` (V5-D01 onward) and `refdocs/changelog/DECISIONS.md` (v4's D-01 to D-82): **settled calls.** Only entries marked Accepted are settled.
3. `refdocs/v5-design/`: **the v5 specs**: roadmap, Blueprint, Build Script, model chain, caching, streaming, verification, follow-ups, visual design, speed, evaluation, deployment.
4. `refdocs/plans/*.md` and `refdocs/execution/*.md`: **what to build, then how and in what order.**
5. `refdocs/guides/`: operational reference (`env_setup.md`, `checklist.md`).
6. `refdocs/synapse-v4-PRD.md`, `refdocs/v4/`, `refdocs/brainstorm-2026-10-16.md`, and the owner's GenUI research in `../research/`: **inherited context**. Where they disagree with v5 docs, v5 wins.

If two current docs disagree, stop and ask. Don't pick one and move on.

---

## Mandatory rules

### 1. Update the changelog after every session
After any session that changed code, made a decision or modified a plan, add an entry to **`refdocs/changelog/CHANGELOG.md`** (format in that file). Even a one-line fix gets a one-line entry.

### 2. Plan before you build
Before any non-trivial feature, a **plan doc** (`refdocs/plans/`) and an **execution doc** (`refdocs/execution/`) exist, with the same filename. If they don't, write them first.

### 3. Log decisions as ADRs
A new architectural or design decision is an entry in `refdocs/v5-design/decisions.md` (Decision, Why, Rejected or trade-off, Status). Unresolved assumptions are marked `ASSUMED:` and surfaced at the next checkpoint.

### 4. Keep docs current
A deviation during execution updates the execution doc. Stale docs are worse than no docs.

### 5. Provenance
Files kept from v4 carry their history in git (`PROVENANCE.md` names the v4 commit). A file ported from any other project starts with a comment naming the source repo, path and commit; read it fully and adapt it.

### 6. Read current docs before using a library or API
FastAPI, Pydantic, Next.js, React, Playwright, esbuild, vitest, the OpenRouter API and the Anthropic SDK change. Read their current docs before writing against them. Do not encode an API from memory.

### 7. Prompts are files; evaluation is live; paid spend needs the owner's go
- Prompt packs live in `api/prompts/` as versioned files. A change records an eval delta (commit prefix `prompt:`).
- **Evaluation is live, never on fakes** (V5-D17): every measurement, go/no-go and demo uses real models, free models first (V5-D22).
- The fake model exists only inside the automated test suite, which never touches the network or spends money.
- Any run that may reach the **paid** Anthropic fallback states a projected amount and waits for the owner's budget. Otherwise set `ALLOW_PAID_FALLBACK=false`.

### 8. Writing style
No em dashes and no en dashes in docs or user-facing text. Use commas, colons, new sentences, and "to" for ranges.

### 9. Language
The product says **Environment** (a simulation or interactive environment), never "lab" (V5-D19). Never abbreviate Environment to `env`. KSSM is one optional curriculum pack, not the product's frame (V5-D20).

---

## The hard constraints (mechanism, not preference)

1. **No unverified Environment is run or operated in the client.** The deliverable is minted only by the verifier; the delivery gate re-derives, re-hashes and re-checks it; the browser re-hashes before rendering. Before verification the host may show only content it renders itself while the Environment is built (escaped text, part names, readout names, a sanitised inert picture), with no numbers and nothing operable, beside a plain status line (Building, Checking, with each check ticked) (V5-D05, accepted 2026-11-14).
2. **The sandbox is exact.** The Environment iframe is `sandbox="allow-scripts"` and nothing else, never `allow-same-origin`. The injected CSP names the configured public origin. No runtime CDN: scripts load only from `/vendor/` and `/vendor/kit/<semver>/` on our own origin, and each `/vendor/` library is admitted by its own decision.
3. **Lanes and labels are honest.** The lane is computed from what the Build Script contains and what verification it survives (V5-D03). Free output is never `canonical` without promotion through the Kit's rules, and every Free generation is logged as a Kit gap candidate. Each part shows what it earned.
4. **Ground before claiming.** `source-verified` requires a Kit science model and a quotation proved word for word against a registered source corpus (V5-D21). Without one the label cannot rise above `model-checked`.
5. **Plan before generating.** Every generated Environment starts from an Environment Blueprint that passes its deterministic checks. Every variable the user changes is worked by hand on a drawn object, with at least one drag or drop (V5-D18).
6. **Micro-components join on evidence.** A Kit part needs a precondition, a manifest signature, an accessibility fence and a registration suite that refuses every planted defect. A science model also needs a cited source, units and domain, an independent reference and properties. A behaviour change bumps the Kit semver. Generated parts join the parts library only by passing their own tests (V5-D13).
7. **The wire is typed once.** Every type that crosses the wire is defined in `packages/schema` and generated into Python. Strict models, fail closed.
8. **Spend is capped and governed.** Every model call goes through the LLM seam and the ledger, including free calls at $0. The paid fallback is refused before sending if it would exceed `LLM_MONTHLY_CAP_USD`.
9. **Evaluation protocol is fixed before runs.** Question sets and their hashes are pinned; a change is a declared amendment. Model-judged scores are never the primary metric. The verifier's planted-defect detection rate is reported, never assumed.
10. **Accessible and phone-first.** 360 px wide, 44 px touch targets, reduced motion respected, a text equivalent for every visual, a keyboard fallback for every gesture. Checked statically and in a real browser.
11. **Provenance is always visible.** The user sees the source, the lane label, which model wrote it, what was checked, and its limits.
12. **Single operator, do not expose.** No auth yet. The API is not reachable from the public internet until the deploy gate in `refdocs/guides/checklist.md` is met, or the owner records a time-boxed waiver.
13. **Repo hygiene.** No secrets, no personal data, no copyrighted source text, no event admin or business material. v5 lives in a **private** GitHub repository, `Azimlearning/Synapse-v5` (created 2026-11-17 when the owner asked for a push; remote `origin`). It stays private until the owner decides otherwise. The read-only `v4` remote is unchanged.

---

## Stack

- **API (`api/`):** Python 3.13, FastAPI, Pydantic v2, SQLite stores, managed with **uv**. Playwright (Python) for the verification harness.
- **Web (`web/`):** Next.js, React, Tailwind, Vitest, managed with **pnpm**.
- **Kit (`packages/kit/`):** micro-components and science models in TypeScript, built by esbuild into versioned bundles.
- **Schema (`packages/schema/`):** TypeScript source of truth, codegen to Pydantic.
- **Models (V5-D22):** OpenRouter free models first (up to three per call, in one request), the paid Anthropic key last. Chains per purpose live in `api/llm/chains.json`.
- **Retrieval:** BM25 first; embeddings only if measured to help.

Observed on the dev machine 2026-11-14: Python 3.13, uv 0.11.26, Node 24.11.0, pnpm 10.28.0.

## Surfaces

One product, four packages. They share source **only** through `packages/schema` (wire types) and the Kit manifest. A change to one does not reach another until its generated artefact is rebuilt.

| Surface | Root | Run | Can | Cannot |
|---|---|---|---|---|
| API | `api/` | `uv run uvicorn api.main:app --reload --port 8000` | Routing, Blueprint, writing, verification, lifecycle, spend | Render UI |
| Web | `web/` | `pnpm --filter web dev` | Chat shell, forming Environment, sandbox host, hash check | Hold secrets, call a model |
| Kit | `packages/kit/` | `pnpm --filter @synapse/kit build` | Micro-components, built to `dist/<semver>/` and a manifest | Server logic, network |
| Schema | `packages/schema/` | `pnpm codegen` | Define wire types | Contain logic |

`api/` and `web/` never import each other.

## Running it

| What | Command |
|---|---|
| Install | `uv sync` and `pnpm install` |
| API | `uv run uvicorn api.main:app --reload --port 8000` |
| Web | `pnpm --filter web dev` |
| Kit | `pnpm --filter @synapse/kit build` and `pnpm --filter @synapse/kit test` |
| Codegen | `pnpm codegen` and `pnpm codegen:check` |
| Tests | `uv run pytest` and `pnpm -r test` (one combined run after a batch of work) |
| Lint and types | `uv run ruff check api eval`, `uv run pyright api eval`, `pnpm -r lint`, `pnpm -r typecheck` |

---

## Build sequence

V5-0 foundations, V5-1 cache and model chain, V5-2 Blueprint and Build Script prototype (live go/no-go), V5-3 Blueprint then one writer in the pipeline, V5-4 forming Environment, V5-5 faster verification, V5-6 visual design, V5-7 change this Environment, V5-8 parts library and caches, V5-9 deployment, V5-10 later. Details: `refdocs/v5-design/roadmap.md`.

**Never build the second of anything until the first is green end to end.**

## When blocked

- **Open question:** check `refdocs/v5-design/open-questions.md`. If unresolved, record an `ASSUMED:` in DECISIONS, proceed, and surface it at the next checkpoint.
- **Doc conflict:** stop, quote both passages, ask.
- **Ambiguous spec:** prefer the safer, more verifiable, less-coupled option, and log the choice.

---

*Companion brief to `refdocs/synapse-v5-PRD.md`. Last updated: 2026-11-14.*
