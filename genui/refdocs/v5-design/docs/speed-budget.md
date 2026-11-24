# Speed budget

## 1. Baseline (MEASURED, v4 traces, 128 questions to 2026-10-29)

| Path | Time | Notes |
|---|---|---|
| Library hit | 0.15 s p50, 0.85 s p90 | No model call |
| Compose | about 24 s | 11.5 s model calls, 12.3 s browser (10 s of which is a fixed interaction window) |
| Free on Opus | about 4 min | 220 s p50 of model calls (175 to 429 s); 9 of the latest 11 runs wrote two or more pages |
| Free page on Opus | 98 s p50, 174 s p90 | 10,394 tokens out p50, 107 tokens/s |
| Free page on Sonnet | 29 s | 6 pages, all refused; **no finished Sonnet Free run on record**. The owner reports about 4 minutes on both models |
| Plan call on Opus | 21 s p50 | Before Free starts |
| Second reader | 2 to 6 s | |
| Explanation | 3.2 s total; first words sooner | Streams |

**Where the 4 minutes go:** a long writer (much of the output is probably thinking), a whole page thrown away and rewritten (the `too long` check runs only after the page is written), a planning call before writing, and a fixed 10 s browser window.

## 2. Targets (TARGET, client-measured from pressing Ask)

| Mark | p50 | p90 |
|---|---|---|
| First words of the explanation | 2 s | 3 s |
| Title and Predict visible | 6 s | 10 s |
| Forming bench picture | 15 s | 25 s |
| Live environment, new or twisted question | 35 s | 60 s |
| Live changed environment | 20 s | 35 s |
| Repeated question (cache) | 1 s | 1 s |

## 3. Levers, with their evidence

| Lever | Expected effect | Evidence | Phase |
|---|---|---|---|
| One writer replaces Plan plus Free page | Removes a call (21 s on Opus, about 5 s on Sonnet) | MEASURED call times | V5-3 |
| Build Script reuses Kit parts | Reply about 1,500 to 2,500 tokens instead of 4,000 to 6,000 visible plus thinking | ESTIMATE, to be measured in the V5-2 prototype | V5-2 |
| `@@BASE` template for twists | Fewer tokens again for twists | ESTIMATE | V5-2 |
| Stop the reply at the first failed unit | Removes most of the 100 to 174 s wasted pages | MEASURED waste | V5-3 |
| Effort setting and model chosen on the twist set | Less thinking time | To measure: `effort` low and medium, standard and fast speed where the model supports `fast` (Anthropic docs: "Not all models support fast") | V5-2 |
| Streaming draft | Perceived wait; no change to the total | Design | V5-4 |
| Explain and write in parallel | Overlaps about 3 s | Design | V5-3 |
| Virtual clock in the browser run | Most of the fixed 10 s | ESTIMATE, gated on L6 | V5-5 |
| Reader in parallel with the browser | 2 to 6 s | MEASURED reader time | V5-5 |
| Warm browser | Chromium start per environment | To measure | V5-5 |
| Change this environment as a patch | 100 to 600 tokens | ESTIMATE; MAIC-UI's paper reports edits under 10 s | V5-7 |
| Caches C1, C4, C7 | Repeats and common twists instant; route and retrieval ready before Ask | Design (`caching.md`) | V5-1, later |

## 4. How time is measured

- **Server stage marks** (v4 traces, kept): every stage with its milliseconds, tokens and cost.
- **Client marks** (new): `t_first_text`, `t_title`, `t_picture`, `t_live`, sent with the request id after delivery.
- **Report:** `eval/speed/report.py` gives p50 and p90 per mark per question set, compared with this baseline, written to an evidence note per run.
- **Wall-clock note:** a v4 trace's `ms` values in the Free lane are cumulative from the lane's start, not per step. v5 records both a start time and a duration per stage so totals cannot be misread.
