# The Environment Blueprint: think first, then build

> Spec for V5-D18. The owner, 2026-11-14:
>
> "before all generation, there must be an initial plan stage where the environment is thought and plan first before passing to ai and also here it must consider that all simulations / environment has interactibility and drag and drop"
>
> and
>
> "if nothing fits template it will generate all from scratch, function of template and prebuilt components is just to assist but not a must".

## 1. Where it sits

```
Route -> Blueprint (think and design) -> plan checks -> Writer (Build Script, carries out the plan) -> checks -> live environment
```

The Environment Blueprint is a short structured design written before any page code. It decides:

- what the environment simulates;
- how the student works it with their hands;
- what they should see happen;
- whether a template, a stored environment or Kit parts help, or whether everything is written from scratch.

The writer then carries out the plan; it does not redesign the environment.

## 2. What the plan contains

| Field | Content | Rule |
|---|---|---|
| `concept` | The science idea in one sentence, at the student's level | Required |
| `goal` | What the student should discover by using the environment | Required |
| `phenomenon` | What is simulated: objects, what moves, what changes | Required |
| `variables` | Each quantity: name, unit, range, role (changed by the student, measured, fixed) | At least one the student changes, at least one measured |
| `interactions` | **For every variable the student changes:** the object they touch, the gesture (drag along, drop onto, rotate, pour, press and hold, pinch), the target, and the motion that responds | Required for every student-changed variable. **At least one drag or drop gesture per environment.** Sliders exist only as the keyboard fallback |
| `scene` | Layout of the bench: the objects, their arrangement, the backdrop | Required |
| `motion` | What animates, and what it shows (bubbles faster when warmer, a mass easing down) | Required. Still frame under reduced motion |
| `science` | The laws or rules: Kit model ids where one fits, otherwise formulas, otherwise "computed by model code" with a description | Required |
| `expected_behaviour` | Statements the checker can test: "extension rises as the load rises", "pH stays between 0 and 14", "period does not depend on mass" | At least two. They become automatic tests (section 5) |
| `assists` | The pattern template, the stored environment used as a base, Kit parts, saved parts. **May be empty: then the writer builds everything from scratch** | Optional |
| `predict` | A prediction question with choices | Required |
| `steps` | 3 or 4 steps, each naming what to drag or drop and what to watch | Required |

## 3. Plan checks (deterministic, no model call)

These run before the writer starts. A failure is sent back to the planner once, with the reason in the checker's words.

- Every student-changed variable has an interaction with a physical gesture on a drawn object.
- At least one drag or drop gesture.
- No interaction is "a slider" or "a button" alone.
- Units are known and consistent; ranges are inside each Kit model's domain where a Kit model is named.
- Named Kit parts and stored environments exist; arguments fit their signatures (v4's PLAN rules where they apply).
- Each `expected_behaviour` refers to declared variables and is one of the testable forms: rises with, falls with, stays within, independent of, equals at a point.

## 4. Speed

The plan is small: about 300 to 700 tokens (ESTIMATE). It runs on a fast tier at low effort, and it streams.

Its fields are also the first things the forming environment shows (`streaming-and-draft.md`): concept, goal, the objects to touch and the prediction. So the plan's time is not dead time for the student. It replaces the v4 Plan call (median 4.8 s on Sonnet, 21 s on Opus, MEASURED), and with a smaller output it should be at the low end of that range (ESTIMATE, measured in V5-2).

## 5. Expected behaviour becomes automatic tests

This is how review is built into generation, as the owner asked (no manual review step):

1. Each `expected_behaviour` statement is compiled into a browser test: sweep the named variable across its range, read the measured one, check the stated relation.
2. Each generated component (a drawing with its handles, a formula block, a script part) is tested on its own as it is assembled: its handles move their controls, its readouts change, its layout passes.
3. A part that passes its own tests and the whole environment's tests enters the parts library as reusable straight away (V5-D13, revised). A part that later fails a test in any environment is withdrawn from the library.

## 6. When nothing fits

If `assists` is empty, the writer writes the whole environment from scratch:

- drawing (SVG or canvas);
- interaction code;
- computation;
- motion.

It still writes inside the house frame and still faces every check. Templates and parts are offered, never required (V5-D16).

## 7. The scene must fill its space (V5-D23)

The `scene` field of the Blueprint states:
- the main apparatus and its approximate share of the bench (at least 55 percent of the width and 50 percent of the height);
- what fills the rest: a scale, an axis, a reference object, a backdrop element;
- how a wide screen is used.

A plan whose scene is a single small object, or that leaves the rest empty, fails a deterministic plan check with the reason, before the writer starts. The fill check in the browser (`verification.md` section 4a) confirms the result.

## 8. As built in V5-2 (2026-11-17)

The checks of section 3 and the scene rule of section 7 are `api/blueprint/checks.py`, rule ids `BP-001` to `BP-010` (v4's `PLAN-0xx` stay with the Compose lane):

| Id | Rule |
|---|---|
| BP-001 | Required fields present, within length limits, names usable and different |
| BP-002 | At least one changed and one measured variable; at most four changed (the house frame holds four controls) |
| BP-003 | Every changed variable has an interaction on a drawn object |
| BP-004 | At least one drag or drop |
| BP-005 | No object or target is a slider, button, checkbox, dropdown or toggle |
| BP-006 | Plain units, ordered finite ranges; where a Kit model is named, its inputs keep its unit and domain |
| BP-007 | Named Kit parts and stored Environments exist; saved parts do not exist yet |
| BP-008 | Each expected behaviour is a testable form with declared variables |
| BP-009 | At least two behaviours, 3 or 4 steps, a prediction with 2 to 4 choices |
| BP-010 | The scene states its apparatus, at least 55 percent of the width and 50 percent of the height, what fills the rest, and how a wide screen is used |

The wire types are `packages/schema/src/blueprint.ts` (generated into `api/schema/generated.py`). `api/blueprint/behaviour.py` compiles each expected behaviour into a `BehaviourSpec` and judges a sweep (`holds`); `api/buildscript/sweep.py` runs the sweep against the page in a real browser. A Blueprint's variable names are the page's ids (V5-D25).
