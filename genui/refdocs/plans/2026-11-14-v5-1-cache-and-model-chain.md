# Plan: V5-1 the exact-match cache and the free-first model chain

> Companion execution doc: [`../execution/2026-11-14-v5-1-cache-and-model-chain.md`](../execution/2026-11-14-v5-1-cache-and-model-chain.md). Decisions: V5-D01, V5-D17, V5-D22 in [`../v5-design/decisions.md`](../v5-design/decisions.md). Specs: [`caching.md`](../v5-design/docs/caching.md), [`model-chain.md`](../v5-design/docs/model-chain.md).

## 1. Why this exists

Two owner calls shape everything after them:

- **A twist must be generated, never answered with a stored lookalike** (V5-D01). v4's library also answers by topic and by name, so "Hooke's law, but two springs in series on Mars" could be served the plain Hooke Environment. 16 of 60 v4 library hits were of that kind (MEASURED).
- **Rate limits must stop mattering** (V5-D22). Free OpenRouter models first, up to three free fallbacks, the paid Anthropic key last. The owner has put their OpenRouter key in `.env` (Q14) and allows providers that may train on prompts (Q15).

Both are small, self-contained and unblock the rest of v5: the new writer (V5-2, V5-3) needs stored Environments as starting material, and every live measurement needs a model chain that does not stall on a rate limit.

## 2. What's already covered

- The service already tries a primary provider, then one fallback, and books every attempt in the ledger (`api/llm/service.py`). OpenRouter becomes the primary (holding its own free-model list) and Anthropic the fallback, so the service itself needs no change.
- The question cache already exists and is exact (`store.remember_question`, `lookup_question_entry`); generated Environments are remembered under their question (`run.py` `_store_and_deliver`).
- The Anthropic provider shows the pattern for streaming, failure mapping and mock-transport tests.

## 3. Scope

**In (V5-1a, the cache):**
- The library serves an Environment only for the same canonical question.
- Topic and name matching no longer serve anything. They become `nearest_labs`, which returns stored Environments as **starting material**, kept on the run for the writer (used from V5-2).
- Tests and the Malay probe updated to the new rule.

**In (V5-1b, the model chain):**
- An OpenRouter provider (chat completions, streaming and not).
- Chains per purpose in `api/llm/chains.json`, validated at load (every free chain id must end in `:free`).
- Free-quota tracking from `GET /api/v1/key`, a per-minute pacer, and skipping OpenRouter for the rest of the UTC day when the daily quota is spent.
- Settings: `ALLOW_PAID_FALLBACK`, `MODEL_CHAINS_PATH`, `OPENROUTER_ALLOW_TRAINING_PROVIDERS`; live mode needs at least one key.
- Factory wiring and `:free` pricing at $0.
- One live free call as a smoke test (the owner's key, free model, no spend).

**Out, with reasons:**
- **Warm-up while typing (C7).** Needs a web change and a new endpoint. Split off as V5-1c so this phase stays small and green.
- **Reader independence** (the second reader must be a different model family from the writer). It needs the writer's model recorded per Environment, which arrives with V5-3. The chain file lists reader candidates now.
- **Choosing models by measurement.** The candidate ids come from third-party trackers dated 2026-10-29 to 2026-11-13 and rotate often. They are a starting point, measured in V5-2.
- **Removing `use_router`, `uncovered` and the name and topic code.** Left in place and unused for serving; deleted in the V5-0 pruning commit once the writer uses `nearest_labs`.

## 4. Approach

**Cache.** `_from_library` keeps the exact-question branch. After a miss it routes locally (no model call) and calls `library.nearest_labs`, which returns up to three stored Environments: the topic's entries ranked by shared words, plus a named match. These go on `run.templates` and into the trace as a `library` record with status `template`, so V5-2 can read them. Nothing is served.

**Model chain.**
- `OpenRouterProvider` posts to `/api/v1/chat/completions` with `models: [up to 3 free ids]` and `provider: {"data_collection": "allow" or "deny"}`. It sends `stream: true` when a watcher is attached.
- The reply's `model` field names the model that answered; it goes to the ledger and the trace.
- Failures are mapped to the existing kinds, with a rule that **no OpenRouter failure stops the run**: 401, 402, 403, 429, 5xx and a refused or empty reply all become `transient`, so the service falls to Anthropic. A truncated reply (finish reason `length`) keeps its usage.
- A chain longer than 3 ids is sent as consecutive groups of 3, at most 2 groups.
- The free quota is read lazily from `GET /api/v1/key` (`free_model_daily_requests`), cached, and refreshed after a 429. When `remaining` is 0, the provider raises a `transient` failure at once (no request is sent) until the next UTC midnight.
- A sliding-window pacer keeps requests under 20 a minute.

**Settings and factory.** Live mode builds OpenRouter first when its key is set, and Anthropic after it when its key is set and `ALLOW_PAID_FALLBACK` is true. The monthly cap is required only when the paid provider will be built. At least one key is always required.

## 5. Risks and unknowns

| Risk | Confidence | Response |
|---|---|---|
| The OpenRouter response shapes differ from the docs (streaming usage, mid-stream errors) | Medium. Read: chat completions request and usage docs, errors, streaming | A live smoke test; mock-transport tests for each shape read in the docs |
| The `models` list limit is 3 | Medium. Stated for the `fallbacks` parameter in the docs and for `models` on a third-party schema page | Groups of 3; a 400 maps to a fallback, not a crash |
| The daily-quota 429 body text is unknown | Low | Detect by a proactive `GET /key` check and by the `X-RateLimit-*` headers; any 429 triggers a refresh |
| Free models return content in `reasoning` and leave `content` empty when reasoning uses the budget | Medium (documented behaviour) | Treat an empty `content` with finish reason `length` as truncated, with usage; leave a generous `max_tokens` to the caller |
| Removing topic hits makes the demo slower for near-library questions | High, and intended | Library questions the seed remembers still hit; twists generate (V5-D01) |
| The owner's free quota is 50 a day if $10 of credit was not bought | Unknown | Ask; the quota check reports `remaining` |
| Free providers may train on prompts | Known | The owner allows it for development (Q15); `OPENROUTER_ALLOW_TRAINING_PROVIDERS=false` turns it off |

## 6. Definition of done

- A question that is not exactly a remembered one is never answered from the library, tested with a topic-level and a name-level question that used to hit.
- `nearest_labs` returns the right stored Environments for a twist, with no model call, tested.
- With a mock transport, the OpenRouter provider: parses a normal and a streamed reply, books $0 for a `:free` model, records the model that answered, maps each failure kind, skips itself on an exhausted daily quota, paces requests, and falls through to Anthropic in the service.
- A chain file that names a paid model in a free chain is refused at load.
- Live mode starts with an OpenRouter key alone (no Anthropic key, no cap) and with Anthropic alone as before, and refuses to start with neither.
- One live free call through the real chain returns text, and the ledger records it at $0 with the model that answered.
- The affected test files pass; the full suite is run once and any failure is explained.
