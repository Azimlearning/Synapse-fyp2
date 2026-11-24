# Execution: V5-2 the Blueprint and the Build Script prototype

> Companion plan: [`../plans/2026-11-17-v5-2-blueprint-and-build-script.md`](../plans/2026-11-17-v5-2-blueprint-and-build-script.md). Per the owner's batch rule, tasks within a slice are built together and tested in one combined run at the end of the slice. A slice must be green before the next starts.

## Before starting

- v5 repo at `119081f` or later; `uv sync` and `pnpm install` done; Kit built (`pnpm --filter @synapse/kit build`).
- CLAUDE.md rule 6: read the current docs for Pydantic v2 (strict models) before writing models by hand, and for Playwright before the browser steps in V5-2d. Do not encode an API from memory.
- No paid call is on the path of slices a to d. V5-2e uses free models with `ALLOW_PAID_FALLBACK=false`.

## Slice V5-2a: the Blueprint

### 1. Wire types
**Files:** `packages/schema/src/blueprint.ts` (new), `packages/schema/src/index.ts`, then `pnpm codegen`.
**Steps:** define `Gesture` (string union), `BlueprintVariable` (`name`, `unit`, `min`, `max`, `role`: `changed | measured | fixed`), `BlueprintInteraction` (`variable`, `object`, `gesture`, `target`, `response`), `BlueprintScene` (`apparatus`, `widthShare`, `heightShare`, `fills`, `wideScreen`), `BlueprintBehaviour` (`kind`: `rises-with | falls-with | stays-within | independent-of | equals-at`, `measured`, `variable`, `low`, `high`, `at`, `text`), `BlueprintAssist`, `Blueprint`. Use only the constructs `to_python.ts` supports; `@int` tags on integer fields.
**Verify:** `pnpm codegen`, then `pnpm codegen:check` and `pnpm --filter @synapse/schema typecheck` exit 0; `api/schema/test_strict.py` still passes and a new case shows an extra field on `Blueprint` is refused.

### 2. The checker
**Files:** `api/blueprint/__init__.py`, `api/blueprint/checks.py`, `api/blueprint/test_checks.py`, `api/blueprint/fixtures/` (JSON).
**Steps:** `check(blueprint, manifest, stored_ids) -> list[Finding]` implementing BP-001 to BP-010 as in the plan, each finding `{rule, path, reason, fix}`. Read the Kit manifest through `api/kitmanifest.py`; do not duplicate its loading. No model call, no I/O beyond reading the manifest.
**Fixtures:** `good_hookes_mars_series.json`, `good_titration_dropper.json`, `good_pendulum_planet.json`, and one `bad_*.json` per rule that must produce exactly that rule's id (BP-001 to BP-010), plus `bad_slider_only.json` for BP-005.
**Verify:** `uv run pytest api/blueprint -q`: every good fixture returns `[]`; every bad fixture returns its rule id and no unrelated ids; findings carry a non-empty reason and fix.

### 3. Expected behaviour to test specs
**Files:** `api/blueprint/behaviour.py`, `api/blueprint/test_behaviour.py`.
**Steps:** compile each `BlueprintBehaviour` into a `BehaviourSpec` (sweep variable, read measured, relation, tolerance) as plain data. A pure helper `holds(spec, samples) -> bool` evaluates a sweep result so the relation logic is tested now; running a sweep in the browser is V5-2d.
**Verify:** `uv run pytest api/blueprint/test_behaviour.py -q`: each of the five relations passes on a conforming series and fails on a violating one, tolerance respected, a constant series is "independent of" and not "rises with".

### 4. The prompt pack
**Files:** `api/prompts/blueprint.v1.md`, and the prompt index test in `api/pipeline/test_prompts.py` if prompts are enumerated there.
**Steps:** a system prompt that asks for the Blueprint as JSON matching the schema, states the BP rules in plain words, and says that assists may be empty. Version header and eval-delta note as the other packs do. No model is called in this slice, so no eval delta yet: record "unmeasured, first live run is V5-2e".
**Verify:** `uv run pytest api/pipeline/test_prompts.py -q` passes.

### Exit of V5-2a
`uv run ruff check api eval`, `uv run pyright api/blueprint api/schema`, `uv run pytest api/blueprint api/schema api/pipeline/test_prompts.py -q`, `pnpm codegen:check`. CHANGELOG entry and STATUS row.

## Slice V5-2b: the Build Script parser, validator and assembler

### 5. Types and the parser
**Files:** `api/buildscript/model.py`, `api/buildscript/parse.py`, `api/buildscript/test_parse.py`. (Internal dataclasses, not wire types: the Build Script does not cross the wire in V5-2.)
**Steps:** sections per `build-script.md` section 2 (`@@BASE` to `@@END`); `PartLine`, `ControlLine`, `FormulaLine`, `ReadoutLine` units; a `units(raw)` iterator that yields each complete unit and stops cleanly on a partial one; `parse(raw)` returns a `BuildScript` or a reason string in the style of `free_house.parse`. Reuse `free_house` helpers (`_sections`, `_lines`, `_items`) by importing them, not copying.
**Verify:** `uv run pytest api/buildscript/test_parse.py -q`: the section 7 worked example parses; a reply cut before `@@END`, a missing required section, an unknown section, a duplicate id and a non-number in a CONTROLS line each give their reason; `units()` on every prefix of the example never yields a half unit.

### 6. The validator
**Files:** `api/buildscript/validate.py`, `api/buildscript/test_validate.py`.
**Steps:** `validate_unit(unit, before, manifest) -> Finding | None` per the table in section 9: text sections (lengths, no markup, no long dashes), PARTS (known component, signature, backward references), CONTROLS, FORMULAS (delegates to task 7), READOUTS (source exists), STYLE and DRAWING (selector scope under `#bench-art`, the v4 scan rules by calling the existing scanner, not a copy), SCRIPT (v4 scan rules plus the `host.*` rules). Whole-reply checks: every control has a handle, every readout has a source, `@@END` present. Move PLAN-020 constants and unit checks in by import from `api/pipeline/plan_checks.py`; if a rule is not importable without the whole Plan type, note it in Deviations and keep it in the Compose lane.
**Verify:** `uv run pytest api/buildscript/test_validate.py -q`: one failing case per row of the section 9 table, each with the right reason; a valid example returns no findings.

### 7. Formulas (slice V5-2c, built here because the validator needs it)
**Files:** `api/buildscript/formula.py`, `api/buildscript/test_formula.py`, `api/buildscript/formula_cases.json`.
**Steps:** a recursive-descent parser for the exact grammar (numbers, names, `+ - * / ^`, parentheses, the listed functions and constants, `deg()` and `rad()`, `pi`); an AST; `evaluate(ast, env) -> float` in Python; `to_js(ast) -> str` emitting a function body; unit propagation for `[unit]` brackets. A single `formula_cases.json` holds expression, environment and expected value, used by both evaluators. The JavaScript is run in the browser harness in V5-2d; here it is run with Node (`node -e`, already installed, 24.11) in a test, so the two evaluators are compared for real without a browser.
**Verify:** `uv run pytest api/buildscript/test_formula.py -q`: every case agrees in Python and Node; 1,000 random inputs per formula agree to 1e-9 relative; division by zero, `ln` of a non-positive, and `sqrt` of a negative are refused in both; a disallowed token (a call to `eval`, a conditional, `time`) is refused with its reason.

### 8. The assembler
**Files:** `api/pipeline/free_house.py` (extended, behaviour for existing replies unchanged), `api/buildscript/assemble.py`, `api/buildscript/test_assemble.py`.
**Steps:** `assemble(script)` builds the page through `free_house.assemble`; FORMULAS become a generated function block in the page script and feed READOUTS; readouts fed by script use `host.readout`. Add the `host` API from section 6 to `HOUSE_SCRIPT` in a way that leaves every existing v4 Free page unchanged (version the script block, do not edit the old one in place).
**Verify:** `uv run pytest api/buildscript/test_assemble.py api/pipeline/test_free_house.py -q`: the new page passes `postprocess` and the L0 scan; the old `test_free_house.py` is untouched and still passes; the page has no `<script src>` and no network call.

### Exit of V5-2b and V5-2c
`uv run ruff check api eval`, `uv run pyright api/buildscript api/pipeline/free_house.py`, `uv run pytest api/buildscript api/blueprint api/pipeline/test_free_house.py -q`. Do not run the whole suite yet (97 minutes; it runs once at the end of V5-2d). CHANGELOG and STATUS.

## Slice V5-2d: fixtures, the prompt and the browser

### 9. Fixture scripts for 5 twists
**Files:** `api/buildscript/fixtures/*.txt`, `api/buildscript/test_fixtures.py`.
**Steps:** write by hand, as a careful human writer would, 5 complete Build Scripts for the twist questions in set T candidates: (1) two springs in series on Mars, (2) a pendulum on another planet with a drag-the-bob handle, (3) titration with a dropper, (4) a ramp with friction and a draggable block, (5) a lens with a draggable object. Each has at least one drag or drop. Each pairs with its fixture Blueprint from slice a.
**Verify:** `uv run pytest api/buildscript/test_fixtures.py -q`: each fixture parses, validates, assembles, and its Blueprint passes the checker.

### 10. The writer prompt
**Files:** `api/prompts/build_script.v1.md`, `api/buildscript/prompt.py` (builds the prompt with the Kit pack from the manifest and the `@@BASE` candidates from `nearest_labs`), tests.
**Steps:** the prompt carries the section list, one worked example, the Kit manifest signatures, the stored Environments offered, and the BP plan as input. Prompt text is a file (rule 7). The Kit pack lists only names, signatures and one-line docs, to stay inside the token budget.
**Verify:** `uv run pytest api/buildscript -q -k prompt`: prompt length under a stated budget (set in the test, recorded in the changelog); the Blueprint appears verbatim; no stored Environment is offered unless `nearest_labs` returned it.

### 11. The real-browser check on fixtures
**Files:** `eval/buildscript/browser_check.py` (new, not in the suite).
**Steps:** read the current Playwright Python docs first (rule 6). For each fixture page: open it in headless Chromium, run the existing Free checks through the harness already in `api/verify`, then run each `BehaviourSpec` as a sweep through the control (keyboard fallback and the drag handle), and compare each formula readout with the Python value.
**Verify:** `uv run python -m eval.buildscript.browser_check`: all 5 fixtures pass every existing check and every behaviour; the output lists per-fixture checks and times. Record in the ledger.

### Exit of V5-2d
One combined run: `uv run ruff check api eval`, `uv run pyright api eval`, `uv run pytest -q` (whole suite, in the background, record the result), `pnpm -r test` after it finishes (not at the same time: the Kit `orbit.test.ts` times out under load). CHANGELOG and STATUS.

## Slice V5-2e: the live gate (needs a valid key)

### 12. Pin the 3 questions
**Files:** `eval/sets/T-gate.json` and its hash in `refdocs/v5-design/docs/evaluation-plan.md` (a declared amendment, protocol rule: sets are pinned before runs).
**Steps:** the owner approves 3 twist questions (suggested: the fixtures' first three). Hash the file; record the hash.

### 13. The gate harness
**Files:** `eval/buildscript/gate.py` (new).
**Steps:** for each question: Blueprint call, checker (one retry with the findings), Build Script call, per-unit validator with early stop (one retry), assemble, browser checks. Settings forced: `ALLOW_PAID_FALLBACK=false`. Report per question: tokens out (thinking included where the provider reports it), writer seconds, attempts, model that answered, findings, $ from the ledger. Print a go or no-go table against the four criteria, marking the time criterion as free-model (A-V5-2-1).
**Verify before the live run:** the harness runs end to end on the fake model inside the automated tests only (it is not an evaluation). Live: `uv run python -m eval.buildscript.gate`, one item first (the harness is alive), then the other two.

### 14. The owner's blind judgement
The owner compares the 3 Environments against v4's Free Environments for the same questions, unlabelled. Record the verdict in the evidence note `refdocs/evidence/2026-11-XX-v5-2-gate.md`.

### 15. Close
STATUS phase row, verification ledger rows, CHANGELOG, ADR notes in `decisions.md` for V5-D02 and V5-D18 (implemented or revised), and a go or recorded no-go with the revised spec.

## Wrap-up checklist

- [ ] CHANGELOG entry per slice, with an honest Verified line.
- [ ] STATUS phase table and ledger rows.
- [ ] `decisions.md` notes for V5-D02, V5-D04, V5-D18 and any new decision (an `ASSUMED:` stays marked until confirmed).
- [ ] `build-script.md` and `blueprint.md` updated for anything the code taught us.
- [ ] Any deviation written below and in the changelog's Deviations line.

## Deviations

- Slice a, task 2: the planted-defect Blueprints are built in the tests by mutating a good fixture (37 cases) rather than stored as `bad_*.json` files: one source of truth.
- Slice a, task 4: the prompt-pack tests are in `api/blueprint/test_prompt.py` (they compare the pack's example with the wire type and the checker's limits), not in `api/pipeline/test_prompts.py`, which still passes unchanged.
- Slices b to d status (2026-11-17): tasks 5 to 10, 12 (drafted, not approved) and 13 are built and tested; task 11 (the separate browser script) is covered by `test_fixtures_browser.py` and `test_sweep.py`; tasks 14 and 15 and the live run wait on the key and the owner.
- Task 6 and 7: the formula unit check is dimension-only and treats bare constants as unknown (V5-D24), after the strict version refused right formulas in the fixtures.
- Task 6: PARTS lines are read and validated but not mounted; `@@BASE` is `none` (see `build-script.md` section 11). Task 10's "`@@BASE` retrieval" moves to V5-3 with the part host.
- Task 12: the set is drafted and pinned with `approved: false`; the gate CLI refuses to run until the owner approves and re-pins (`uv run python -m eval.v5.sets --pin T-gate`). Its questions were changed from the first draft because one was the writer prompt's worked example.
- Task 13: the logic is `api/buildscript/gate.py` (testable on a fake model); `eval/buildscript/gate.py` is the CLI.
- Slice a: `ruff format` is not enforced in this repo (40 of 57 existing files fail it), so it was not run on the new files; `ruff check` and `pyright` are clean.
