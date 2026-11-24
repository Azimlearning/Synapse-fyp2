# Caching in v5: seven layers, one rule

> **The rule (V5-D01, the owner's, 2026-11-01): a stored environment is served as the answer only for a question that is the same as one already answered. Anything close but different is generated, and the stored work is used as starting material.**
> Outside research supports it. A 2025 study by Zaharia, Gonzalez and co-authors found that correct and incorrect semantic-cache hits have heavily overlapping similarity scores, so no static threshold guarantees a right answer. For a generated environment, a near-match would be silently wrong: an environment for a different question.

## The layers

| Layer | What is stored | Key | Serves the answer? | What it saves |
|---|---|---|---|---|
| **C1 Question cache** | The verified environment for a question | Canonical question (lowercase words, single spaces); later, a reviewed paraphrase list per environment | **Yes**, and only on an exact key | The whole generation (< 1 s) |
| **C2 Template retrieval** | Stored environments' Build Scripts | Topic, Kit parts used, content words, an embedding | No: given to the writer as `@@BASE` | Writing what already works; most of a twist |
| **C3 Parts library** | Generated parts (a drawing, a handle set, a formula block) that passed their own tests and the whole environment's checks (V5-D13) | Concept and part kind | No: offered to the writer like Kit parts | Rewriting good drawings; Level 3 tokens |
| **C4 Pre-built twists** | Environments generated ahead of time for likely twists of each library environment ("on the Moon", "double the mass", "in series") | Canonical question of the twist | Yes, but only through C1 (an exact key) | The wait for the most common twists |
| **C5 Provider prompt cache** | The stable prompt prefix: core rules, the Build Script spec, pattern templates | Prompt prefix | n/a | Input cost and some first-token latency |
| **C6 Verification results** | Which checks a given exact HTML passed, with the Kit hash | HTML hash plus Kit hash | n/a | Re-running the browser for an identical page. **The delivery gate still re-hashes and re-checks the stored row every time (v4 hard constraint 1)** |
| **C7 Warm-up while typing** | Route, template retrieval and the Kit pack, prepared before Ask | Debounced draft question | n/a | Route and retrieval time; **no model call, no spend** before Ask |

## Rules for each layer

**C1.**
- The canonical key is v4's `canonical_question`.
- Paraphrases are added to an environment's key list only by a person, or by a paraphrase check that was itself measured against labelled pairs (open question Q6).
- A Kit semver bump marks entries stale until re-verified (v4 rule).

**C2.** Retrieval may be loose, because a wrong template only costs a worse starting point. The writer can also reply `@@BASE none`.

**C3: parts library lifecycle.** This follows the lifecycle in v4's brainstorm (`declared`, `verified`, `cached`, `audited`, `reviewed`, `canonical`, plus `stale`, `evicted`, `rejected`):

1. A part is tested on its own as its environment is assembled: handles move their controls, readouts change, layout passes, and the Blueprint's expected behaviours hold.
2. When it and its environment pass, it is reusable at once (V5-D13, the owner's call: tests instead of a manual review).
3. A part that fails in any later environment is withdrawn, and environments that use it are rebuilt.
4. It becomes `canonical` only when promoted into the Kit, with a registration suite (hard constraint 6). A part is never `source-verified` on its own.

**C4.**
- Generated in a batch run with a stated projected cost and the owner's typed amount (v4 rule 7).
- Each pre-built twist is a normal verified environment.
- It is served only for its own exact question. A near question uses it through C2 as a template, never as the answer.

**C5.** Built in v4 (`PROMPT_CACHING`, off). Turn on after one measured run shows the saving.

**C6.** An optimisation, not a trust shortcut. On any doubt (a different Kit hash, a changed verifier version), the cached result is ignored.

**C7.** Local only; nothing is sent to a model before Ask (spend rule).

## How a question flows through the layers

```
"Hooke's law but two springs in series on Mars"
  C7  route and retrieval already warm from typing
  C1  exact key? no
  C2  nearest templates: hookes_spring (Hooke bench), planet_gravity (planets bench)
  C3  reviewed parts: none for series springs yet
  C5  prompt prefix cached
  ->  writer replies in Build Script, @@BASE hookes_spring, reusing massHanger, planetGravity, weight
  ->  verified, stored under its canonical key (C1), its drawing enters C3 as `verified`
"hookes law but two springs in series on mars" (asked again)
  C1  exact key: yes -> live in under a second
```

## Measuring the caches

| Layer | Measure |
|---|---|
| C1 | Hit rate on real traffic; any reported wrong hit (a flag) |
| C2 | Share of writer replies that use a `@@BASE`; tokens saved compared with `@@BASE none` on the twist set |
| C3 | Parts offered, parts used, parts promoted |
| C4 | Pre-built twists served; spend per pre-built twist |
| C5 | Cached input tokens per call (the ledger already prices them) |
| C6 | Browser runs skipped |
| C7 | Time from Ask to the writer's first token, with and without warm-up |
