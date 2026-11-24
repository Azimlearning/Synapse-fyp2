# Change this environment

> Spec for V5-D06. It finishes accelerator 3 of the owner's GenUI plan, "edit, not regenerate". MAIC-UI (Tsinghua, arXiv 2604.25806) reports full regeneration at 200 to 600 s, and diff edits in under 10 s per its paper.

## 1. What the student can do

- Type a follow-up under an environment: "now do it on the Moon", "make the masses heavier", "add air resistance".
- Tap a **suggested twist** chip under the environment. The writer proposes two or three with each environment, in `@@TWISTS` (added to the Build Script spec; host text, never run).
- Each change makes a new environment with its own checks and label, linked to its parent. The old environment stays one tap away.

## 2. Request

`/ask` gains optional fields, typed in `packages/schema`:

| Field | Meaning |
|---|---|
| `parent_env_id` | The environment being changed |
| `state` | Current control values and the Predict answer, sent by the host from the bridge's `synapse_event` messages |

The server loads the parent's stored Build Script (`architecture.md` section 5). If the parent is a v4 environment with no script, it uses the parent's Plan, or treats the follow-up as a new question with the parent as `@@BASE`.

## 3. Writer reply: a patch

```
@@PATCH
@@TITLE
Two springs in series on the Moon
@@PARTS
planet = planetPicker {"start": "moon"}
@@PREDICT
On the Moon, will the springs stretch more or less than on Mars?
- More
- Less
Check: switch the planet and compare the extension.
@@END
```

- Only changed sections appear.
- In PARTS, CONTROLS, FORMULAS and READOUTS, a line replaces the line with the same name. `name = delete` removes one.
- The merge is deterministic and done by Synapse.
- The merged script then goes through **every** check, exactly as a new environment. Nothing is trusted because the parent passed.

Expected size: about 100 to 600 tokens (ESTIMATE), so the change is mostly checking time.

## 4. Starting state

The new environment starts with the parent's control values where the control still exists, so the student continues where they were. The values are passed as start values and checked like any other.

## 5. Limits and rules

- Cache: a changed environment is stored under its own canonical question (the follow-up plus the parent id), so the same change on the same environment is instant next time.
- Spend: a change is a paid call through the ledger like any other.
- Depth: changes of changes are allowed. Each stores its parent. The chain is shown as a small breadcrumb.
- Safety: a follow-up is also checked by intake for prompt injection, and a patch cannot delete the house frame's safety parts (the frame is not in the script).

## 6. Measures

| Measure | TARGET |
|---|---|
| Time to the live changed environment, p50 | 20 s or less |
| Patch passes first time | 80 percent or more |
| Share of follow-ups that use a suggested twist | Reported |
