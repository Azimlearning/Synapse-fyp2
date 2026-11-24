# Plan: V5-2 the Blueprint and the Build Script prototype, then the live go/no-go

> Companion execution doc: [`../execution/2026-11-17-v5-2-blueprint-and-build-script.md`](../execution/2026-11-17-v5-2-blueprint-and-build-script.md). Decisions: V5-D02, V5-D04, V5-D13, V5-D16, V5-D17, V5-D18, V5-D23 in [`../v5-design/decisions.md`](../v5-design/decisions.md). Specs: [`blueprint.md`](../v5-design/docs/blueprint.md), [`build-script.md`](../v5-design/docs/build-script.md), [`evaluation-plan.md`](../v5-design/docs/evaluation-plan.md) section 3.

## 1. Why this exists

v4's Free lane takes about 4 minutes and $0.48 to $1.03 per Environment, and its plan step cannot express a twist the Kit has no part for. V5-2 builds the two pieces that replace it and finds out, cheaply and live, whether they hold before the pipeline is rebuilt around them (V5-3):

- **The Environment Blueprint** (V5-D18): a short structured design, made before any page code, that checks deterministically that every changed variable is worked by hand on a drawn object, with at least one drag or drop, and that the scene fills its space.
- **The Build Script** (V5-D02, V5-D04): one writer reply in labelled sections, Kit parts and model-written parts side by side, each unit checkable on arrival, with formulas compiled by us in preference to model code.

## 2. What is already there (read 2026-11-17)

- `api/pipeline/free_house.py` (253 lines): the sectioned reply `free.v7`, its parser (`parse`) and the house frame (`assemble`). The Build Script extends it; it is not replaced.
- `api/pipeline/plan_checks.py` (1,067 lines, PLAN-001 to PLAN-023): v4's rules for Kit-based plans. Some move into the Build Script validator (units, domain, constants, scene scale); the rest stay with the Compose lane.
- `packages/schema` holds wire types as TypeScript interfaces; `pnpm codegen` emits `api/schema/generated.py`; `codegen:check` guards drift. Supported constructs are listed in `codegen/to_python.ts` (interfaces, string unions, arrays, records, no generics, no `extends`).
- The model chain (V5-1b) is built and mock-tested, but not yet proved live: the OpenRouter key in `.env` is still rejected (HTTP 401, re-run 2026-11-17).

## 3. Scope, in the order it is built

Per the rule "never build the second of anything until the first is green", each slice is green end to end (code, tests, docs) before the next starts.

| Slice | Builds | Needs the key? |
|---|---|---|
| **V5-2a Blueprint** | `Blueprint` wire types in `packages/schema` with codegen; a deterministic checker (`api/blueprint/`) with its own rule ids `BP-001` onward; the prompt pack `blueprint.v1.md`; 5 fixture Blueprints (3 that pass, plus the failing ones the checker must refuse) | No |
| **V5-2b Build Script** | Parser and unit splitter (`api/buildscript/`) over the section list in `build-script.md` section 2; per-unit validator (section 9) with v4 PLAN rules moved in where they fit; the assembler on `free_house.py` | No |
| **V5-2c Formulas** | Grammar and parser; a JavaScript emitter for the page; a Python evaluator for the reference; unit propagation where inputs carry units | No |
| **V5-2d Fixtures and prompt** | `build_script.v1.md` with Kit pack and `@@BASE` retrieval; fixture scripts for 5 twists that pass every existing check, run through the real browser harness | No (browser only) |
| **V5-2e Live gate** | 3 twist questions from set T, live, on the free chain, `ALLOW_PAID_FALLBACK=false` | **Yes** |

Out of scope here, with reasons:
- **Blueprint streaming and the forming Environment** (V5-4). V5-2 produces the Blueprint whole.
- **Wiring into `run.py`** (V5-3). V5-2 is a prototype behind its own entry points and the eval harness; the pipeline is not touched, so v4's behaviour and tests cannot regress.
- **`expected_behaviour` compiled to browser tests** is built in V5-2a as a data structure and a compiler to test specs; running the specs in the real browser is V5-2d on the fixtures, and V5-3 on every generation.
- **Pattern templates and the writer choosing them** (G1, V5-10). Only the stored-Environment base (`@@BASE`) is used, via `nearest_labs` from V5-1a.

## 4. Approach

**Blueprint.** TypeScript source of truth: `Blueprint`, `BlueprintVariable`, `BlueprintInteraction`, `BlueprintScene`, `BlueprintBehaviour` and a `Gesture` union (`drag`, `drop`, `rotate`, `pour`, `press-hold`, `pinch`; the keyboard fallback is implicit, never a gesture). Strict Pydantic via codegen. The checker is pure Python with no model call and returns a list of `{rule, path, reason, fix}` in the checker's own words, the same shape as v4's plan findings, so one retry can quote them.

Rules (ids are new; v4's `PLAN-0xx` stay with the Compose lane):

| Id | Rule |
|---|---|
| BP-001 | Required fields present and in length limits |
| BP-002 | At least one student-changed and one measured variable |
| BP-003 | Every student-changed variable has an interaction on a drawn object with a physical gesture |
| BP-004 | At least one `drag` or `drop` gesture in the whole Blueprint |
| BP-005 | No interaction is a slider or a button alone |
| BP-006 | Units known; ranges inside a named Kit model's domain |
| BP-007 | Named Kit parts and stored Environments exist and their arguments fit their signatures |
| BP-008 | Each `expected_behaviour` names declared variables and is one of: rises with, falls with, stays within, independent of, equals at a point |
| BP-009 | At least two `expected_behaviour` statements; 3 or 4 steps; a prediction with 2 to 4 choices |
| BP-010 | The scene states the apparatus and its share of the bench (at least 55 percent of width and 50 percent of height), what fills the rest, and how a wide screen is used (V5-D23) |

**Build Script.** A pure-Python parser into a typed `BuildScript`, a unit iterator that yields each complete unit as it would arrive from a stream, and a validator that takes one unit plus the units before it (backward references only). Early stop on the first failed unit returns the reason in the checker's words. The assembler adds the new sections to `free_house.assemble` (`@@PARTS` chips and Kit mounting come later, in V5-3, once the Kit part host exists; V5-2 assembles FORMULAS, CONTROLS, READOUTS, DRAWING, STYLE and SCRIPT, which is everything the 5 fixtures need).

**Formulas.** A small recursive-descent parser over the exact grammar in `build-script.md` section 5; an AST evaluated by a Python function and emitted as JavaScript by a separate emitter. Both are tested against the same table of cases so they cannot diverge, and a property test compares them over random inputs. Units: simple dimensional algebra over the base set already used by the Kit (`N`, `m`, `kg`, `s`, `m/s`, and so on); an expression whose inputs carry no unit is not unit-checked.

**Where the code lives.** New packages `api/blueprint/` and `api/buildscript/` beside `api/pipeline/`, each with its own tests. They import `api/schema/generated.py` only for wire types and share nothing with `web/`.

## 5. The live gate (V5-2e)

As `evaluation-plan.md` section 3, adapted to free models (V5-D22):

- 3 twist questions from set T (drafted and pinned 2026-11-17 in `eval/v5/`, not yet approved by the owner). None may be the question the writer prompt shows as its worked example; the first draft was, and was changed before any run.
- Blueprint then Build Script, fakes off, ledger on, `ALLOW_PAID_FALLBACK=false`.
- **Go if all hold:** median tokens out 2,500 or fewer including thinking; median writer time 20 s or less; at least 2 of 3 scripts validate and pass the existing Free checks on the first or second attempt; the owner judges the 3 Environments at least as good as v4's Free Environments.
- **Caveat recorded in advance.** The time criterion was set for a paid standard-tier model. Free models are slower and rate-limited, so a time miss on free models is reported as such and does not by itself make a no-go; the other three criteria are unchanged. This is an `ASSUMED:` (A-V5-2-1) to confirm with the owner at the checkpoint.
- The harness reports tokens, time, attempts, model that answered and $0 from the ledger. The owner's blind judgement is a person's, never a model's.

## 6. Risks and unknowns

| Risk | Confidence | Response |
|---|---|---|
| No valid OpenRouter key, so slice V5-2e cannot run | Certain today (401 on 2026-11-17) | Slices a to d need no key and go first; the owner supplies a key before V5-2e |
| A free model cannot follow the sectioned format or the Blueprint's field list | Medium | The per-unit validator reports reasons in plain words and retries once; the gate measures first-or-second-attempt validity; a no-go revises `build-script.md` |
| BP-010 (scene fill) is hard to state deterministically from text | Medium | Check the stated shares and the presence of fill elements in the plan; the browser fill check (V5-6) confirms the result. A false pass here is caught later, a false refusal wastes one retry |
| Formula JS and Python evaluators diverge on edge cases (division by zero, `ln` of a non-positive, floating rounding) | Medium | One shared case table, a property test, explicit refusal of non-finite results in both |
| The generated Pydantic cannot express a field (codegen is deliberately narrow) | Low | Keep types within the supported constructs; extend codegen only with a test |
| Doc conflict: Q11 (is the "assistant" reading right) is unconfirmed | n/a | `ASSUMED:` A-V5-2-2 below; V5-2 uses only `@@BASE` and Kit parts as optional assists, which fits either reading |

## 7. Assumptions (surface at the next checkpoint)

- **A-V5-2-1** Free-model writer time is judged separately from the go criteria (section 5).
- **A-V5-2-2** The "Free lane assistant" reading in `genui-engine.md` section 2 holds (Q11). V5-2 builds nothing that depends on the unconfirmed half (pattern templates chosen by the writer).
- **A-V5-2-3** The "stere" note in the owner's earlier message is not designed; nothing in V5-2 depends on it (asked in the handoff, still unanswered).

## 8. Definition of done

- A fixture Blueprint that breaks each of BP-001 to BP-010 is refused with that rule's id and a reason; 3 good fixtures pass; `pnpm codegen:check` and `uv run pytest api/blueprint` pass.
- The Build Script parser accepts the worked example in `build-script.md` section 7 (once its Kit part names are checked against the manifest) and refuses a truncated reply, an unknown section, a forward reference, a formula using a disallowed token, and a script using a refused API, each with its reason.
- The formula evaluators agree on the shared case table and on 1,000 random inputs per formula, and both refuse a non-finite result.
- 5 fixture twists assemble into pages that pass `postprocess`, the L0 scan and the real-browser checks the Free lane already uses, with no change to those checks.
- Nothing in `api/pipeline/run.py` or `web/` changed; the existing suites for them are untouched.
- The live gate is run and recorded, or V5-2e is recorded as Blocked on the key, with slices a to d marked Done.
