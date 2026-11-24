# Execution: V5-1 the exact-match cache and the free-first model chain

> Companion plan: [`../plans/2026-11-14-v5-1-cache-and-model-chain.md`](../plans/2026-11-14-v5-1-cache-and-model-chain.md). Per the owner's batch rule, tasks are built together and tested in one combined run (task 9).

## Before starting

- v5 repo at `c0632af` or later; `uv sync` and `pnpm --filter @synapse/kit build` done.
- The owner's `.env` exists (Q14). It is read only by the application, never by Claude's tools.
- OpenRouter API docs read on 2026-11-14: chat completions, streaming, errors, model fallbacks, usage accounting, provider routing, limits.

## Tasks

### 1. The cache serves only the same question (V5-1a)
**Files:** `api/pipeline/run.py` (`_from_library`, `_Run.templates`), `api/pipeline/library.py` (`nearest_labs`).
**Steps:**
1. Add `library.nearest_labs(question, entries, by_topic, limit=3)`: topic entries ranked by `best_entry`'s overlap, then a name match from `match_by_name`, deduplicated, at most `limit`, no side effects.
2. Add `_Run.templates: list[dict]` (empty by default).
3. In `_from_library`: keep the exact-question branch unchanged. After a miss, route locally; fill `r.templates` from `nearest_labs`; add a trace record `library` with status `template` listing the plan ids; **serve nothing**.

**Verify:** `uv run pytest api/pipeline/test_run_library.py -q` (after task 2 updates its expectations) passes, and a test asserts that a question about a stored topic that is not a remembered question makes model calls and records `templates`.

### 2. Update the tests for the cache (V5-1a)
**Files:** `api/pipeline/test_run_library.py`, `api/models/test_malay.py` only if it asserts a served hit.
**Steps:** tests that expected a topic or name hit now assert: no environment is served from the library, the model is called, `templates` holds the expected plan, and the trace says `template`. Exact-question hits stay as they are. Add one new test for a twist ("Hooke's law with two springs in series on Mars") that must not be served the Hooke Environment.
**Verify:** the file passes.

### 3. Chains file and loader (V5-1b)
**Files:** `api/llm/chains.json`, `api/llm/chains.py`, `api/llm/test_chains.py`.
**Steps:** a `Chains` loader reading `chains` (name to ids) and `purposes` (purpose to chain name) and `default`. Validation: every id ends in `:free`; each chain is 1 to 6 ids; every purpose names a known chain; unknown purposes use `default`. `chains.json` holds the 2026-11-14 candidates from `docs/model-chain.md` section 4.
**Verify:** `uv run pytest api/llm/test_chains.py -q` passes (valid file loads; a paid id, an empty chain, an unknown chain name and malformed JSON are each refused with a message naming the problem).

### 4. The OpenRouter provider (V5-1b)
**Files:** `api/llm/providers/openrouter.py`, `api/llm/providers/test_openrouter.py`.
**Steps:**
- `OpenRouterProvider(api_key, chains, *, allow_training=True, base_url, client, clock, pacer)`.
- `model_for(tier)` returns the first id of the default chain (used for pricing and the ledger reservation; the actual model is the reply's `model`).
- `complete(request, model, on_text)`: choose the chain by `request.purpose`; split into groups of 3, at most 2; for each group post `{"models": [...], "messages": [system?, user], "max_tokens", "provider": {"data_collection": ...}}`; `stream: true` with `on_text`. Skip SSE comment lines. Accumulate `choices[0].delta.content`; ignore `delta.reasoning`; read `usage` from the final chunk; read `model` from any chunk; a chunk with `error` or finish reason `error` is a failure.
- Failures: every HTTP error and every refused, empty or malformed reply is `transient` with a reason that holds only the status and the error code. A finish reason `length` with usage is `truncated` with that usage. Timeouts are `timeout`.
- Quota: `GET /api/v1/key`, lazy, cached; `remaining == 0` makes `complete` raise `transient` at once until the next UTC midnight; any 429 refreshes it.
- Pacer: at most 20 requests in any 60 seconds; waits instead of failing.

**Verify:** `uv run pytest api/llm/providers/test_openrouter.py -q` passes with a mock transport covering: plain reply, streamed reply, reasoning-only chunks, a mid-stream error, 401, 402, 429, 5xx, a malformed body, a truncated reply, the groups of 3, the data-collection field, the quota skip, the pacer, and that no key or prompt appears in any failure message.

### 5. Pricing, settings and the factory (V5-1b)
**Files:** `api/llm/pricing.py`, `api/core/settings.py`, `api/llm/factory.py`, `api/llm/test_service.py` (updated), `refdocs/guides/env_setup.md`.
**Steps:**
- `price_for`: provider `openrouter` with a model ending `:free` costs 0; any other OpenRouter model is priced as the dearest known.
- Settings: `allow_paid_fallback: bool = True`, `model_chains_path: Path | None`, `openrouter_allow_training_providers: bool = True`. `missing_for_mode` in live mode: at least one of the two keys; the monthly cap only when Anthropic will be built (key set and `allow_paid_fallback`); an absolute ledger path always.
- Factory: build OpenRouter when its key is set; Anthropic when its key is set and paid fallback is allowed; OpenRouter primary, Anthropic fallback.
- Document the three settings and the changed live-mode rule in `env_setup.md`.

**Verify:** `uv run pytest api/llm -q` passes. New tests: OpenRouter alone builds; Anthropic alone builds as before; neither raises `ConfigError` naming both keys; `ALLOW_PAID_FALLBACK=false` with both keys builds OpenRouter only and needs no cap; a free call books $0 with the answering model in the ledger; a failing OpenRouter falls through to Anthropic and books the paid cost.

### 6. A live smoke test (V5-1b)
**Files:** `eval/llm/smoke.py` (new, not part of the suite).
**Steps:** a script that loads the real settings (reads `.env` inside the process), builds the service with `ALLOW_PAID_FALLBACK` forced off, sends one short request for each of the three chains, prints the model that answered, tokens, cost and elapsed time, never the key. It stops if the free quota reports 0.
**Verify:** run it once. Expected: three replies, cost $0.0000 each, a `:free` model id. Record the result in STATUS.

### 7. Docs
**Files:** `refdocs/changelog/CHANGELOG.md`, `refdocs/STATUS.md`, `refdocs/v5-design/roadmap.md` (V5-1 now says warm-up moved to V5-1c), `refdocs/v5-design/decisions.md` (V5-D01 and V5-D22 implementation notes).

### 8. Combined run
Run, once: `uv run ruff check api eval`, `uv run pyright api eval`, `uv run pytest api/llm api/core api/pipeline api/routes api/models -q`. Record each result. Then the full `uv run pytest -q` in the background and record its result when it finishes.

## Wrap-up checklist

- [ ] CHANGELOG entry with an honest Verified line.
- [ ] STATUS phase table and ledger row.
- [ ] V5-1a and V5-1b implementation notes in `decisions.md`.
- [ ] Any deviation written here and in the changelog's Deviations line.

## Deviations (2026-11-14)

- Task 6: the smoke runs as `uv run python -m eval.llm.smoke` (a script path cannot import `api`), and `eval/llm/__init__.py` exists for it.
- Task 5: `env_ignore_empty=True` was added to the settings (and `api/core/test_settings_empty.py`), because a blank `LLM_MONTHLY_CAP_USD=` line from the `.env` template crashed loading.
- Task 8: the full suite was not run in one piece: the v4 baseline run was still going on the same machine, and a second concurrent run would have caused the timeouts seen in the Kit tests. Affected files were run instead (see the changelog).
- Task 6 did not pass: the owner's key is rejected by OpenRouter (HTTP 401).
