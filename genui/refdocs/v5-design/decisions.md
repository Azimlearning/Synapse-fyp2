# Synapse v5 decisions

> Format: Decision, Why, Rejected or trade-off, Status.
> Status is one of:
> - **Accepted** (the owner said so; the date and words are given);
> - **Agreed in principle** (direction accepted, wording to confirm);
> - **Proposed** (Claude's recommendation, not yet accepted);
> - **Open** (needs the owner).
>
> Only Accepted entries are settled. v4's DECISIONS.md (D-01 to D-82) still applies where v5 does not change it.

## V5-D01: The cache answers only a repeated question
**Decision.** A stored environment is served as the answer only when the question's canonical form matches one already answered. A question near a stored environment, including a twist, is generated, with the stored environment as a template (`docs/caching.md`). This supersedes v4 D-42's topic and name hits.
**Why.** The owner (2026-11-01): "sometime user ask something already is in our data but a little twist which makes it unique so free flow generation is still needed, and library hit is only when something is same or basically cached". Research shows near-match cache hits cannot be made reliably correct by a similarity threshold. In v4, 16 of 60 library hits came from topic or name matches.
**Trade-off.** More paid generations: questions v4 answered for free now cost money and time.
**Status.** Accepted, 2026-11-01. **Built 2026-11-14 (V5-1a):** `library.nearest_labs`, `_from_library`; tested.

## V5-D02: One writer, in Build Script, uses Kit parts and model-written parts together
**Decision.** The separate Compose assembly and whole-page Free call become one writer replying in Build Script (`docs/build-script.md`). It names Kit parts where they fit and writes the rest itself, up to the whole environment from scratch. An Environment Blueprint comes first (V5-D18, revised 2026-11-14), and the writer carries it out.
**Why.** v4's Free lane takes about 4 minutes, on both Opus and Sonnet by the owner's account. Most of the reply rewrites what the Kit already has, and a page is often written twice. The owner wants "free + compose kit" together.
**Rejected.** Running Free and Compose in parallel (pays twice, v4 D-76). A model switch alone (the owner reports both take about 4 minutes).
**Status.** Accepted direction, 2026-11-09 (the owner: "i agree"). The format's details stay Proposed until the V5-2 gate.

## V5-D03: The lane is computed from the script
**Decision.** A script with only Kit parts and Kit-fed readouts is Compose and may earn `source-verified`. Any formula, model drawing or model script makes it Free, which is `model-checked` at most. Each part carries its own badge.
**Why.** v4 hard constraint 3 says a lane is decided by what verification the output survives. Computing it from content makes that literal.
**Status.** Proposed.

## V5-D04: Numbers come from the most checkable source that can express them
**Decision.** In order of preference:
1. a Kit science model;
2. a `@@FORMULAS` line, which Synapse compiles to JavaScript and recomputes in Python;
3. model-written code in `@@SCRIPT`, for anything formulas cannot express: time-stepped simulation, collisions, particles, randomness with a fixed seed, 3D.

Readouts fed by model code go through `host.readout` and are marked "computed by model code, browser-checked". They are tested against the Blueprint's expected behaviour.
**Why.** The owner, 2026-11-14: the Free lane must "generate theoretically everything". The first draft (no model-written arithmetic at all) would have capped what the lane can express.
**Trade-off.** Code-computed numbers get no independent recomputation. They get behaviour tests, the second reader and the browser run, and the label stays `model-checked`.
**Status.** Proposed (revised 2026-11-14).

## V5-D05: The forming environment
**Decision.** While an environment is written and checked, the host shows what it forms: escaped text, part names, readout names and a sanitised inert picture, with no numbers and nothing operable. It carries **no "Draft" label** (the owner, 2026-11-14: "no need to say draft"). A plain status line shows the stage (Building, Checking, with each check ticked), so the user can see it is not ready yet and what has passed. Hard constraint 1 is reworded as in `docs/streaming-and-draft.md` section 2.
**Why.** The owner wants an environment that appears as it is written, as ChatGPT's does.
**Trade-off.** It reverses the owner's call of 2026-10-22 (no draft view). A student may briefly see a draft that is then refused.
**Rejected.** Running unverified code in the draft. Streaming raw HTML into the frame.
**Status.** Accepted, 2026-11-14 (Q3).

## V5-D05b: An operable Kit-only draft (later)
**Decision.** Possibly allow a draft built only from Kit parts with manifest-validated arguments to be operated before verification.
**Status.** Open, V5-10.

## V5-D06: Change this environment, by patch
**Decision.** Follow-ups carry the parent environment and its state. The writer returns a patch, Synapse merges it, and the result goes through every check as a new environment.
**Why.** The owner agreed to follow-ups; accelerator 3 of the owner's GenUI plan.
**Status.** Accepted direction, 2026-11-09.

## V5-D07: Model, effort and speed chosen by measurement
**Decision.** The writer's model, `effort` and `speed` are chosen on the twist set at the V5-2 gate. The standard tier is the default. The demo-day `GENERATION_TIER=heavy` is retired.
**Why.** The owner: Opus or Sonnet "dosent really matter since they both take about 4 minutes". The format, not the model, is the fix.
**Status.** Proposed.

## V5-D08: v5 is the build that finishes the owner's GenUI plan
**Decision.** v5 is organised as the GenUI engine (`docs/genui-engine.md`):
- the three levels inside one reply;
- the Free writer working from templates and components;
- the 13 accelerators from v4's Amendment A1.5;
- the research gaps G1 to G8 as the long-term list.
**Why.** The owner (2026-11-09): "i want synapse v5 to be the biggest improvement ... leverage more on the genui concept that i have been developing (the free lane assistant with templates and components ... and also the caching)".
**Status.** Accepted direction, 2026-11-09. The interpretation of "free lane assistant" is to confirm (Q11).

## V5-D09: Faster verification, gated by the detection rate
**Decision.** A virtual clock, a warm browser, the reader in parallel and a result cache. Each is accepted only if the L6 rate does not fall and the hostile set still passes.
**Status.** Proposed.

## V5-D10: Layout checks join the verifier
**Decision.** Text collisions, overflow, minimum text and handle size, bench position on a phone and contrast are checked in the browser for every environment.
**Status.** Proposed.

## V5-D11: Deployment
**Decision.** Either the full deploy gate, or a time-boxed waiver with an access code on Render plus Vercel.
**Status.** Open (Q4).

## V5-D12: Seven caching layers; near-matches are templates, never answers
**Decision.** Layers C1 to C7 as in `docs/caching.md`.
**Status.** Proposed (C1's rule is Accepted through V5-D01).

## V5-D13: A parts library that grows from verified generations, reviewed by tests, not by hand
**Decision.** Each generated part is tested on its own as it is assembled: its handles move their controls, its readouts change, its layout passes, and the Blueprint's expected behaviours hold. A part that passes its own tests and the whole environment's tests is reusable at once. A part that later fails in any environment is withdrawn. Promotion into the Kit still follows the Kit's rules (hard constraint 6).
**Why.** The owner, 2026-11-14: "skip review, we need to integrate the review or SOP within the code generation itself, or test of each component generation instead of all".
**Trade-off.** No person looks at a part before it spreads. The per-part tests, and withdrawal on failure, carry that risk.
**Status.** Accepted, 2026-11-14.

## V5-D14: Start from a copy of v4, in a new private repository with history
**Decision.** As in `docs/how-to-start-v5.md`.
**Rejected.** From scratch (it rebuilds the trust engine, the most expensive and best-tested part). Inside the v4 repository (v4 is public and frozen for the final).
**Status.** Proposed (Q1). Implemented 2026-11-17 at the owner's request to push: a private repository, `Azimlearning/Synapse-v5`. The decision itself is still the owner's to accept.

## V5-D15: v4 stays frozen through the final
**Decision.** No v5 work enters v4. A fix needed in both goes to v4 first and is merged into v5.
**Status.** Proposed.

## V5-D16: The Free lane can generate anything; templates and parts assist, never constrain
**Decision.**
- No topic limit and no catalogue limit.
- The writer may draw with SVG or canvas, animate, simulate and compute anything the exact sandbox allows (v4 hard constraint 2 unchanged).
- Vetted libraries may be served from `/vendor/` (for example a 2D physics engine or a 3D renderer), each admitted with its licence and a pinned version.
- When no template, stored environment or part fits, the whole environment is written from scratch.

**Why.** The owner, 2026-11-14: "make sure it can generate theoretically everything"; "function of template and prebuilt components is just to assist but not a must".
**Trade-off.** From-scratch environments are slower and checked less deeply than Kit environments, and their label says so.
**Status.** Accepted, 2026-11-14. Which `/vendor/` libraries to admit is Proposed, one decision per library.

## V5-D17: Evaluation is live, never on fakes
**Decision.** Every measurement, go/no-go and demo uses the live model. The fake model remains only inside the automated test suite, which must never touch the network or spend money. Paid runs still state their cost and wait for the owner's budget. This amends v4 rule 7's "Fakes are the default" for everything outside the test suite.
**Why.** The owner, 2026-11-14: "never do fake, I'll tell you budget later".
**Status.** Accepted, 2026-11-14.

## V5-D18: An Environment Blueprint before any generation, designed for hands-on interaction
**Decision.** Every generated environment starts with an Environment Blueprint (`docs/blueprint.md`). It covers:
- what is simulated;
- for every variable the student changes, the object they touch and the gesture (at least one drag or drop per environment);
- the scene and motion;
- the science source;
- testable expected behaviours;
- optional assists.

Deterministic plan checks run before the writer starts. The plan streams into the forming environment first.
**Why.** The owner, 2026-11-14: "there must be an initial plan stage where the environment is thought and plan first before passing to ai and also here it must consider that all simulations / environment has interactibility and drag and drop".
**Trade-off.** One extra model call (small, fast tier, streamed), against a writer that no longer designs and writes at the same time.
**Status.** Accepted, 2026-11-14.

## V5-D19: General simulations and environments, not a KSSM lab
**Decision.**
- v5 generates simulations and environments for any question, starting with general science.
- It is built so that other domains, engineering first, can follow with their own parts, sources and packs.
- The word "lab" leaves the product's language.
- The artifact is an Environment (v4's term).
- The plan is the Environment Blueprint and the writer's format is the Environment Build Script (the owner chose options 1 and 3, 2026-11-14).

**Why.** The owner, 2026-11-14: "drop the narrative of kssm to general simple science simulation / environment + drop lab narrative into simulations / environments. this is for future dev of all generation (like engineering) not just form 4 and 5 science".
**Trade-off.** The KSSM-specific polish (syllabus routing, textbook citations, Malay) is no longer the default experience.
**Status.** Accepted, 2026-11-14.

## V5-D20: KSSM becomes the first optional curriculum pack
**Decision.** A curriculum pack bundles a syllabus's topic list, its registered source corpora, its language overlays and its teaching extras. KSSM is the first pack:
- the Form 4 and 5 topic router;
- the KSSM textbook corpus;
- Bahasa Melayu;
- the exam mirror;
- the Amali lab report.

With no pack selected, the router classifies by general field and the extras stay off. A later pack (another syllabus, an engineering course) follows the same shape.
**Why.** The owner chose "Optional curriculum pack", 2026-11-14.
**Status.** Accepted, 2026-11-14.

## V5-D21: The top label is `source-verified`, earned against any registered source
**Decision.** `kit-verified` is renamed `source-verified`. It needs a Kit science model and a quotation proved word for word against a registered source corpus: a textbook, a standard or a reference handbook. The KSSM textbooks are one registered corpus. Hard constraint 4 reads "source" for "textbook".
**Why.** The owner chose "any authoritative cited source", 2026-11-14.
**Trade-off.** Each new corpus needs its own position on licence and quotation (the v4 A-8 question, asked per corpus).
**Status.** Accepted, 2026-11-14.

## V5-D22: Free OpenRouter models first, up to three free fallbacks, the paid Anthropic key last
**Decision.** Every model call goes through a per-purpose chain (`docs/model-chain.md`):
1. one OpenRouter request listing up to three `:free` models, which OpenRouter fails over between;
2. then Anthropic direct with the paid key, behind the ledger and cap;
3. then the pipeline's degrade ladder.

When OpenRouter reports the shared daily free quota is spent, it is skipped until the next UTC day. The second reader is always a different model family from the writer.
**Why.** The owner, 2026-11-14: free models such as NVIDIA Nemotron, "up to 3 fallback free llm" because of rate limits, "last choice is my paid anthropic api key".
**Trade-off.**
- The free quota is shared across all free models (50 requests a day, or 1,000 a day after buying $10 of credits), so fallbacks protect against one busy model, not against the daily cap.
- Free model quality is unmeasured.
- Some free providers may train on prompts.
**Status.** Accepted, 2026-11-14. The candidate model ids are Proposed and measured before use. Providers that may train on prompts are allowed (owner, 2026-11-14, Q15); revisit before any public deploy. **Built 2026-11-14 (V5-1b):** `api/llm/providers/openrouter.py`, `chains.py`, `chains.json`, the three settings and the factory, tested with mock transports; the live check is blocked on a valid OpenRouter key.

## V5-D23: No empty or big white spaces in an Environment
**Decision.** The Blueprint, the house frame and the verifier all enforce that an Environment is filled (`docs/visual-design.md` section 5, `docs/verification.md` section 4a):
- the Blueprint says how the scene fills its space;
- the house frame reflows panels so no column leaves a dead area, and the apparatus scales to fill the bench;
- a browser **fill check** measures empty space at 360, 768 and 1280 px (and 1920 px), light and dark, and refuses an Environment with a large empty region, a bench the picture does not fill, or a blank band between blocks.

The check applies to Kit Environments and to generated ones.
**Why.** The owner, 2026-11-14, with a screenshot of a stored v4 Kit Environment (Wave speed): the wave picture is small inside a wide bench card, and a large empty area sits under the bench beside the graph. They asked that v5 ensure "no empty or big white spaces in the simulation".
**Trade-off.** Thresholds are ASSUMED until calibrated on the stored Environments, so the first calibration may refuse some good ones. Kit scenes that fail need a Kit change and a relock.
**Status.** Accepted, 2026-11-14. The thresholds are Proposed.

## V5-D24: Formula units are checked by dimension, and a bare constant stands the check down
**Decision.** A FORMULAS line's units are checked by **dimension** (a length added to a time, a force declared as a length, a sine of a length are refused) and not by scale (cm against m). A number written in a formula other than a small whole number or one half may stand for a constant with a unit, so an expression that contains one makes its unit unknown and the check stands down for it. A bare number joined to a quantity by `+`, `-`, `min` or `max` takes that quantity's unit. An unknown unit switches the check off for the expression; it never guesses.
**Why.** Real formulas are full of bare constants (`/ 1000`, `* 9.81`, `t - 273`, `25 * 0.1 / c`). A strict check that tracked scale refused right formulas and would have cost a free model a retry each time (found writing the five fixtures on 2026-11-17: `mass_g / 1000 [kg]`, `volume - 25` and `max(0, a)` were all refused). What it still catches is the clear case: named quantities of unlike dimension combined or declared wrongly.
**Rejected or trade-off.** (a) Track scale too: false refusals, as above. (b) Add a literal-with-unit syntax (`25[cm3]`): the grammar becomes ambiguous with the declared-unit bracket and the writer must learn another form. (c) No unit check at all: loses the one deterministic check on a model-written law. **Cost:** a scale slip with a bare constant (`* 100` where `* 1000` was meant) is not caught here; the second reader reads every formula for it, and the label stays `model-checked`.
**Status.** Proposed, 2026-11-17. Implemented in `api/buildscript/formula.py` and tested.

## V5-D25: A Blueprint's variable names are the page's ids
**Decision.** In a Build Script, the id of each control is the name of a Blueprint variable whose role is `changed`, and each `measured` variable is the name of a formula (or control) that one of the readouts shows. The writer prompt states it, and the browser sweep (`api/buildscript/sweep.py`) relies on it to run the Blueprint's expected behaviours against the page.
**Why.** The Blueprint's expected behaviours become automatic tests only if the test can find the control to sweep and the readout to read. Matching by name is deterministic. Without it a behaviour that cannot be tested would be silently skipped, or a model would be asked to map names (a model-judged step in a safety check).
**Rejected or trade-off.** (a) A mapping field in the Build Script: more for the writer to get wrong. (b) Let a model map the names: not deterministic. **Cost:** the writer's names are constrained, and a behaviour whose measured quantity no readout shows is a failure, not a skip (so a writer cannot pass by leaving the quantity out).
**Status.** Proposed, 2026-11-17. Implemented and tested on the five fixtures.

## V5-D26: Claude through OpenRouter credits for the slow steps of a live demo, behind the cap
**Decision.** A second, PAID chains file (`api/llm/chains-paid.json`, `"paid": true`) lists Claude models reached through the owner's OpenRouter credits: Haiku 5.5 for the short steps, Sonnet 5.5 for writing a whole page. It is built as the paid provider in place of the Anthropic key when `ALLOW_PAID_FALLBACK=true`, `OPENROUTER_PAID_CHAINS_PATH` names it and `LLM_MONTHLY_CAP_USD` is set. `PAID_FIRST_PURPOSES` lists the purposes sent to it FIRST, with the free models second (the viva setting: plan, free, blueprint, build_script, fill, patch, wording, wording_free; route and explain stay free first). Every paid call is reserved against the model its purpose uses, plus the provider's thinking allowance, and booked in the ledger at the larger of OpenRouter's reported cost and the price table's.
**Why.** Measured 2026-11-24 on the real Plan request for a new question: the best free model (Nemotron 3.5 Super) took 193 s and 17,896 reasoning tokens; Claude Haiku 5.5 took 14 s ($0.0027); Sonnet 5.5 took 16 s ($0.045). A live demo cannot wait minutes per step. Both Anthropic keys in the two `.env` files were refused (HTTP 401), and the owner added OpenRouter credits and asked that generation be rerouted to Claude when the Free lane is needed (2026-11-24).
**Trade-off.**
- This departs from V5-D22's free first order for the listed purposes; the free models are still tried when Claude fails.
- A whole new Free-lane page still takes about 4 to 12 minutes, mostly Sonnet writing (about 40 tokens a second through OpenRouter), and cost $0.10 to $0.35 each on 2026-11-24.
- A paid chains file must not list `:free` ids and a free one must not list paid ids; both are refused at load.
**Status.** Accepted by the owner's instruction, 2026-11-24. Cap for the viva: $3 a month in genui's ledger. Built and tested (`api/llm/test_paid_chains.py`, 8 tests; `api/llm` and `api/core` 127 passed), and run live: 5 new Environments generated and verified for $1.01.

Also found 2026-11-24 (not a new decision): with `OPENROUTER_ALLOW_TRAINING_PROVIDERS=false` OpenRouter excludes the NVIDIA free endpoints, so only rate-limited models remain and every request gets HTTP 429. `start-synapse.ps1 -SimMode live` now sets it to true (Q15 already allows it). The free reasoning allowance was raised from 4,096 to 16,384 tokens: 4,096 cut every Plan off.
