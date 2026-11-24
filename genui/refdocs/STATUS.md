# Synapse v5: Build Status

> Read this first. Updated at the end of every build session. Phases come from [`v5-design/roadmap.md`](v5-design/roadmap.md).
> Status words:
> - **Not started**
> - **In progress** (say exactly what works)
> - **Done** (built and verified by a run)
> - **Blocked** (name the blocker and who unblocks it)
>
> Never round up. v4's status, kept for its history, is in [`v4/STATUS-v4.md`](v4/STATUS-v4.md).

**2026-11-14:** v5 created as a local repository copied from v4 at `9e8b27e` (full history; the read-only `v4` remote points at the v4 folder). Dependencies installed, the Kit rebuilt to its locked hash, codegen checked. The v4 test suite was re-run unchanged as v5's baseline: Kit 758 of 759 passed (one orbit audit test times out at 5 s, and it also times out in the untouched v4 repo on this machine); the Python suite passed 1450 (1 skipped), web 150. No v5 feature is built yet.

## Phases

| Phase | Scope | Status |
|---|---|---|
| V5-0 | Foundations: repository, baseline, CI, timing harness, pinned question sets, pruning, v5 operating docs | In progress: repository, install, Kit build, codegen check and operating docs done; baseline run (Kit 758 of 759, web 150, Python 1450 passed); speed report built (2026-11-17: `eval/speed/report.py`, reproduces the v4 compose and free baselines from traces, not the library figure); question sets R, T, N, W, F drafted and pinned but NOT approved by the owner; CI inherited from v4 and not yet run on v5; client timing marks and pruning not started |
| V5-1 | Cache answers repeated questions only (V5-1a); the free-first model chain (V5-1b); warm-up while typing (V5-1c, split off) | V5-1a and V5-1b built and tested with mock transports (118 and 45 tests passed). **Blocked on a valid OpenRouter key:** the live smoke got HTTP 401 for all three calls. V5-1c not started |
| V5-2 | Blueprint and Build Script prototype, then the live go/no-go on 3 twists | In progress. Slices a to d built and tested (2026-11-17): the Blueprint (wire types, checker BP-001 to BP-010, behaviour specs, prompt pack); the Build Script (parser, per-unit validator BS-000 to BS-008, formula compiler to JavaScript and a Python evaluator, assembler on the house frame); five fixture scripts that pass every check and the real browser; the writer pipeline and the gate harness on a fake model. 321 tests in `api/blueprint` and `api/buildscript`. Nothing has run against a real model. **Slice e (the live gate) is blocked on two things:** a valid OpenRouter key, and the owner's approval of the three draft questions in `eval/v5/T-gate.json` |
| V5-3 | Blueprint then one writer in the pipeline; early stop; lane computed; per-part badges | Not started |
| V5-4 | Forming Environment (streaming draft) | Not started. V5-D05 wording accepted 2026-11-14 |
| V5-5 | Faster verification without weaker verification | Not started |
| V5-6 | Visual design and layout checks | Not started |
| V5-7 | Change this Environment and suggested twists | Not started |
| V5-8 | Parts library, pre-built twists, prompt cache | Not started |
| V5-9 | Deployment | Not started. Needs Q4 and Q5 |
| V5-10 | Later items | Not started |

## Baseline carried from v4 (MEASURED, v4 `data/traces.jsonl`, 128 questions to 2026-10-29)

| Path | Time | Cost |
|---|---|---|
| Library hit | 0.15 s median, 0.85 s at p90 | $0 |
| Compose | about 24 s | about $0.05 |
| Free (Opus) | about 4 min (175 to 429 s of model calls) | $0.48 to $1.03 |
| Free (Sonnet) | 6 pages of about 29 s each, all refused; the owner reports about 4 minutes on both models | n/a |

## Decisions waiting

[`v5-design/open-questions.md`](v5-design/open-questions.md):
- **The OpenRouter key**: the one in `.env` is rejected (72 characters, does not start with `sk-or-`). An OpenRouter key starts with `sk-or-v1-` (https://openrouter.ai/keys).
- **Q14 follow-up**: whether $10 of OpenRouter credits was bought (free quota 50 a day without it, 1,000 with it).
- **Q4 and Q5**: deploy and corpus.

## Verification ledger

| Date | What was verified | How | Result |
|---|---|---|---|
| 2026-11-14 | v5 setup from the v4 copy | `uv sync`; `pnpm install --frozen-lockfile`; `pnpm --filter @synapse/kit build`; `pnpm codegen:check`; `uv run playwright install chromium` | All exit 0. Kit 0.1.0 rebuilt to `cee6673166f5`, 65 manifest entries. 17 GB free on C: |
| 2026-11-14 | v5 baseline, Kit tests | `pnpm -r test` in v5, unchanged code | Kit 758 passed, 1 failed of 759 (`orbit.test.ts`, test timed out in 5000 ms). The same test also times out in the v4 repo when run alone, with the Python suite running in parallel, so it is machine load, not the copy. Web tests did not run because pnpm stopped at the first failure: rerun with `pnpm --filter web test` |
| 2026-11-14 | V5-1: exact cache and free-first chain | `uv run ruff check api eval`; `uv run pyright` on the changed files; `uv run pytest api/llm api/core`; `uv run pytest api/pipeline/test_run_library.py api/models/test_malay.py`; `uv run python -m eval.llm.smoke` | Lint and types clean; 118 passed; 45 passed (273 s); the live smoke FAILED: HTTP 401 on all three calls, the key is not accepted by OpenRouter. Full suite and browser smokes not rerun on the new code |
| 2026-11-17 | V5-1 live smoke, rerun | `ALLOW_PAID_FALLBACK=false uv run python -m eval.llm.smoke` | FAILED again: HTTP 401 on all three calls, $0 spent. The key in `.env` is still not accepted by OpenRouter; it needs the owner |
| 2026-11-17 | V5-2a Blueprint | `pnpm codegen:check`; `pnpm --filter @synapse/schema typecheck`; `uv run ruff check api eval`; `uv run pyright api/blueprint api/schema`; `uv run pytest api/blueprint api/schema api/pipeline/test_prompts.py -q` | All clean; 128 passed (62 in `api/blueprint`: 3 good fixtures pass, 37 planted defects each refused by their rule, every relation of the behaviour specs passes and fails correctly, prompt example matches the wire type). Prompt never sent to a model |
| 2026-11-17 | V5-2b to d: Build Script, formulas, fixtures, writer, gate | `uv run ruff check api eval`; `uv run pyright api/buildscript api/blueprint eval/buildscript`; `uv run pytest api/buildscript api/blueprint -q`; `uv run python -m eval.buildscript.gate` | Clean; 296 passed (56 s) then the gate and writer tests 25 passed. Real Chromium: 5 of 5 pages pass `verify_environment`; every readout matches the Python reference at 9 settings per page; every Blueprint behaviour holds on its page; Node and Python agree on 41 cases and 1,650 random inputs. The gate CLI refuses the unapproved set. No model was called. Full Python suite and `pnpm -r test` not rerun on this code |
| 2026-11-17 | Combined run on all V5-1 and V5-2 code | `uv run pytest -q` (full, 60 min); then after the last fixture edits `uv run pytest api/buildscript api/blueprint eval/v5 eval/speed`; `uv run ruff check api eval`; `uv run pyright api eval`; `pnpm codegen:check`; `pnpm --filter web test`; `pnpm --filter @synapse/kit test` | Python 1814 passed, 1 skipped (baseline 1450; the full run began before the last fixture label fixes, which the 330-test rerun covers); ruff, pyright and codegen clean; web 150 passed; Kit 759 of 759 passed (the `orbit.test.ts` timeout did not recur when nothing else was running) |
| 2026-11-14 | v5 baseline, web tests | `pnpm --filter web test` | 150 passed in 22 files (pnpm had stopped at the Kit failure before reaching them) |
| 2026-11-14 | v5 baseline, Python tests | `uv run pytest -q` in v5 (started before the V5-1 edits; modules are imported at collection, so it ran the copied v4 code, though a few files may have been picked up late) | 1450 passed, 1 skipped, 1 warning in 5853 s (1 h 37 min). Together with Kit 758 of 759 and web 150: the copy is as green as v4 was |
