# The model chain: free models first, the paid key last

> Spec for V5-D22. The owner, 2026-11-14:
>
> "we want to change from using a multi llm system using openrouter using some free models like nvidia nemotron and other free models and backups or fallbacks (maybe up to 3 fallback free llm) this is because sometime its rate limited, last choice is my paid anthropic api key"
>
> Facts below were read on 2026-11-14 from OpenRouter's docs (model fallbacks, limits) and three third-party trackers. Free model lineups rotate often: **re-check the ids before every measured run.**

## 1. Shape

```
For each call (route, explain, blueprint, build script, reader, patch):
  1. OpenRouter, one request: models = [free A, free B, free C]   (all ":free", so the request stays free)
       OpenRouter itself fails over on errors, rate limits, downtime and moderation refusals
  2. If that fails, or the daily free quota is spent: Anthropic, direct, with the paid key
       behind the spend ledger and LLM_MONTHLY_CAP_USD, refused before sending if over the cap (hard constraint 8)
  3. If that fails: the pipeline's existing degrade ladder (simple environment, then the honest "no environment" note)
```

## 2. What the free tier allows (read 2026-11-14)

| Fact | Source |
|---|---|
| `:free` models: 20 requests a minute | OpenRouter free-models page; trackers |
| 50 free requests a day; **1,000 a day once the account has bought $10 of credits** (counted all time; spending the balance later does not lower it) | Same |
| The daily quota is **shared across all free models**; extra keys or accounts do not raise it | OpenRouter limits docs; trackers |
| Failed attempts count toward the daily quota | OpenRouter free-models page |
| A negative balance can return `402` even on free models | OpenRouter limits docs |
| `GET /api/v1/key` returns `free_model_daily_requests` (used, limit, remaining) | OpenRouter limits docs |
| A `models` list that ends in a paid model is billed at that model's price if used; to stay free, list only `:free` models | OpenRouter model-fallbacks docs |
| Some free providers may train on prompts (one tracker: 10 of 16, October 2026) | Third party, unverified |

**What this means for Synapse.** A question takes about 5 to 8 model calls: route, explain, blueprint, build script, two readers, sometimes a retry.
- At 50 a day, that is roughly 6 to 10 questions before every call falls through to the paid key.
- At 1,000 a day, it is roughly 125 to 200.
- The three free fallbacks protect against **one model** being busy or down. They cannot extend the **daily** quota, because it is shared.

## 3. Behaviour that keeps the free quota useful

- **Quota check.** The service reads `GET /api/v1/key` at start-up and caches `free_model_daily_requests`. When `remaining` is 0, or a `429` says the daily cap is reached, OpenRouter is skipped until the next UTC day, so failed attempts do not burn the paid fallback's time.
- **Per-minute pacing.** A small local limiter keeps under 20 requests a minute. A burst waits a few seconds rather than failing.
- **One model per answer, recorded.** OpenRouter's response names the model actually used. It goes into the trace and the ledger (at $0 for free models), so every environment says which model wrote it.

## 4. Chains per purpose (initial candidates, to be measured)

Ids as listed 2026-11-14. The chains live in a settings file (`api/llm/chains.json`), not in code, because the lineup rotates.

| Purpose | Free A | Free B | Free C | Paid last resort |
|---|---|---|---|---|
| Blueprint and Build Script (hardest) | `nvidia/nemotron-3-ultra-550b-a55b:free` | `thinkingmachines/inkling:free` | `poolside/laguna-s-2.1:free` | `claude-sonnet-5-5` |
| Explain, route, patch (fast) | `nvidia/nemotron-3.5-lightning:free` | `google/gemma-4-31b-it:free` | `nvidia/nemotron-3.5-super-vl:free` | `claude-haiku-5-5` |
| Second reader (L4) | A different family from the writer that wrote the page (for example Gemma or Inkling when Nemotron wrote it) | | | `claude-sonnet-5-5` |

**Reader independence.** The second reader must not be the model that wrote the page. The chain picks the reader from a different family than the writer actually used.

Each candidate is kept or dropped by measurement on the question sets (`evaluation-plan.md`):
- pass rate of Blueprints and Build Scripts;
- time;
- refusals.

## 5. What changes in the code (v4 paths)

| File | Change |
|---|---|
| `api/llm/providers/openrouter.py` (new) | OpenAI-compatible chat completions with streaming and the `models` list. Reads `model`, usage and the `X-RateLimit-*` headers. Read the current OpenRouter API docs before writing (rule 6) |
| `api/llm/chain.py` (new) | Per-purpose chains, the quota check, per-minute pacing, falling through to Anthropic, the reader-independence rule |
| `api/llm/factory.py` | Live mode builds the chain: OpenRouter when `OPENROUTER_API_KEY` is set, Anthropic as the last resort when `ANTHROPIC_API_KEY` is set. Either alone works |
| `api/llm/pricing.py` | `:free` ids price at $0; the ledger records them with their model id |
| `api/core/settings.py` | `OPENROUTER_API_KEY`, `MODEL_CHAINS_PATH`, `ALLOW_PAID_FALLBACK` (default true; false during free-only evaluation), `OPENROUTER_ALLOW_TRAINING_PROVIDERS` (owner: allowed, 2026-11-14, Q15; revisit before any public deploy) |
| `api/llm/providers/fake.py` | Unchanged: the test suite still never touches the network |

## 6. Consequences

- **Evaluation can be live at $0** (V5-D17). With `ALLOW_PAID_FALLBACK=false`, a measured run uses only free models and costs nothing. It stops when the daily quota is reached and reports how far it got.
- **Quality is unknown.** Free models may write weaker Blueprints and Build Scripts than Sonnet. The verifier catches broken pages, not dull ones. This is measured, not assumed.
- **Prompt caching** (C5) applies only on the paid Anthropic path.
- **Privacy.** Learner questions go to whichever free provider serves them. Synapse sends no personal data by design, but a learner can type anything. Whether providers that may train on prompts are allowed is the owner's call (Q15).
