# Evaluation plan

> Fixed before any v5 run, as v4 hard constraint 9 requires. The sets and their hashes are pinned in V5-0. A change to a set is a declared amendment. Model-judged scores are never the primary metric.

## 1. Question sets

| Set | Size | What it holds | Why |
|---|---|---|---|
| **R: repeats** | 10 | Exact questions already in the library | C1 must serve them in about 1 s with no model call |
| **T: twists** | 20 | A library environment plus a change that matters: another planet, series or parallel, a different liquid, a heavier mass, an added factor | v5's main case: must be generated, and should reuse the base |
| **N: new** | 10 | Science questions with no library environment ("how does a black hole bend light", "why do clouds form at a height") | The Free end of the ladder |
| **W: wild** | 5 | Off-syllabus or playful ("simulate a cat falling on its feet") | "Ask anything" in a demo |
| **F: follow-ups** | 10 | An environment plus a change request | Change this environment |
| **H: hostile** | v4's 20 | Attack pages and questions | Unchanged: every one blocked by two layers |
| **L6: planted defects** | v4's suite plus the new rows | Defects the verifier must refuse | The detection rate is reported, never assumed |

The T, N, W and F sets are written by the owner, or drafted by Claude and approved by the owner, before the first paid run. They are stored with a SHA-256 in `eval/v5/`.

## 2. Metrics

| Metric | Primary? |
|---|---|
| Environments delivered per question (any environment, by lane) | Yes |
| Live-environment time p50 and p90 (client) | Yes |
| First visible marks (`speed-budget.md`) | Yes |
| First-attempt pass rate, and refusals by reason | Yes |
| L6 detection rate and false positives | Yes |
| Cost per delivered environment | Yes |
| Layout check pass rate | Yes |
| Share of T replies using `@@BASE`; tokens out | Diagnostic |
| Owner's blind visual judgement (`visual-design.md`) | Yes, a person, not a model |
| Second reader issues per environment | Diagnostic only |
| Design reader score (later) | Never primary |

## 3. The V5-2 prototype gate (go or no-go)

**Run:** 3 questions from T, Build Script on the standard tier, fakes off, the ledger on.

**Projected cost (ESTIMATE):** up to about $0.30, plus retries. **Ask for $1.00 and stop there.** Nothing runs until the owner types an amount (rule 7).

**Go if all of these hold:**

- Median tokens out is 2,500 or fewer (thinking included).
- Median writer time is 20 s or less.
- At least 2 of 3 scripts validate and pass the existing Free checks on the first or second attempt.
- The owner judges the 3 environments at least as good as v4's Free environments.

**No-go:** write down which assumption failed, revise `build-script.md`, and try again before building V5-3.

## 4. Full measurement (end of V5-7)

Sets R, T, N, W and F on the chosen model and effort.

**Projected cost (ESTIMATE):** about $0.10 to $0.25 per generated environment. That is about $5 to $12 for 45 generated environments, plus repeats at $0. The amount is stated and confirmed before the run, as always.

**Report:** an evidence note with every metric beside the v4 baseline.

## 5. Run order (every paid run)

1. Fakes pass.
2. One item live (the harness is alive).
3. The stated set.
4. Evidence note.
5. STATUS ledger row.
