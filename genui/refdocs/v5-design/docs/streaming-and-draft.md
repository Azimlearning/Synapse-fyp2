# Streaming and the forming environment

> Spec for V5-D05. The owner agreed in principle on 2026-11-09. This **reverses the owner's call of 2026-10-22** (no "not fully checked" draft view), so it needed the owner's wording: accepted 2026-11-14 with **no "Draft" label** ("no need to say draft"). A plain status line stays, so the user can see the stage and the checks passed (hard constraint 11).

## 1. What the student sees, second by second (TARGET)

| Time | Shown | Source | Can the student operate it? |
|---|---|---|---|
| 0 to 2 s | Explanation streaming into the chat; a forming card with "Building your environment" | Explainer; host UI | n/a |
| 2 to 6 s | Title, kicker, Try this, the Predict card | Build Script text sections | **Yes, the Predict card.** It is host UI, not part of the environment. The answer is kept and compared when the environment arrives |
| 4 to 10 s | Steps; chips naming each part ("Planet gravity: Kit, source checked", "Spring stiffness: new") | `@@STEPS`, `@@PARTS` | No |
| 8 to 15 s | Empty readout cards; an inert picture of the bench | `@@READOUTS`; `@@DRAWING` sanitised, or a Kit scene's static preview | No |
| 15 to 35 s | "Checking: second reader, browser run" with ticks as each passes | Stage events (v4) | No |
| Live | The live environment replaces the forming card in place; Predict says "now test your prediction" | Verified Environment | Yes |

If checks fail and a retry starts, the forming card says so in one line, and the text sections stay. If the final outcome is a simple environment, it replaces the forming card the same way.

## 2. The trust line

| Allowed before verification | Never allowed before verification |
|---|---|
| Host-rendered text from validated text sections, escaped, with no markup | Any model-written script running anywhere |
| A sanitised SVG shown as an image (`<img>` from a `blob:` URL of the sanitised SVG), so it cannot run code or load anything | The model's HTML in the DOM or in the environment frame |
| Part names, Kit badges, readout labels | Readout values (no numbers until the environment computes them) |
| A plain status line on the card: Building, then Checking with each check ticked (no "Draft" label) | Any control, handle or drag on the forming Environment |

**SVG sanitiser (server side, then again in the host).**
- Keep an allowlist of shape and text elements and presentation attributes.
- Remove `script`, `foreignObject`, every `on*` attribute, `href` and `xlink:href` (except same-document `#id` gradients), `style` blocks that contain `url(` or `@import`, and anything else.
- Cap the size.
- On any doubt, show no picture rather than a partial one.

**Proposed wording for hard constraint 1 (V5-D05):**

> No unverified Environment is run, operated or placed in the environment frame. Before verification, the client may show host-rendered content: escaped text, part names, readout names and a sanitised inert picture, with no numbers, nothing operable and a plain status line (accepted 2026-11-14). The deliverable is still minted only by the verifier, re-checked at the gate and re-hashed in the browser.

A later option (V5-D05b, not in v5.0): a Kit-only draft that the student can operate. All its code is audited Kit code with manifest-validated arguments. It would still be a draft.

## 3. Wire events (in `packages/schema`, generated into Python)

| Event | Fields | Sent when |
|---|---|---|
| `draft_open` | `draft_id`, `base_title?` | The writer starts |
| `draft_text` | `draft_id`, `field` (title, kicker, try, predict, steps, idea), `value` (plain text or a typed list) | A text section validates |
| `draft_part` | `draft_id`, `name`, `kind` (kit, formula, control, generated), `component?`, `badge` | A PARTS, CONTROLS or FORMULAS line validates |
| `draft_readout` | `draft_id`, `id`, `label` | A READOUTS line validates |
| `draft_picture` | `draft_id`, `svg` (already sanitised) | DRAWING validates and sanitises |
| `draft_status` | `draft_id`, `stage` (writing, checking, retrying, simple), `note` | Stage changes |
| `environment` (v4) | As v4 | Verified. The client replaces the draft |
| `draft_close` | `draft_id`, `outcome` | Done |

Strict models, fail closed (hard constraint 7). The v4 `code` event stays, shown only in the "See how it's built" disclosure.

## 4. Server side

- The provider stream is read into a **unit splitter**: it yields a section when the next marker arrives, and a line inside PARTS, CONTROLS, FORMULAS and READOUTS when the newline arrives.
- Each unit is validated (`build-script.md` section 9). A valid unit emits its draft event. An invalid one cancels the provider stream (the ledger books what was spent) and starts the retry with the reason.
- The assembler starts as soon as `@@SCRIPT` closes, while `@@HINTS` and `@@EXPLAIN` still stream.

## 5. Client side

- `FormingLab` component: the same frame and layout as the live environment (bench first, `visual-design.md`), so the swap does not jump.
- Uses `aria-live="polite"` for new parts.
- With reduced motion, parts appear without animation.
- The Predict choice is kept in component state and sent to the environment through the v4 bridge when it goes live.
- Client timing marks: `t_first_text`, `t_title`, `t_picture`, `t_live`, reported to the server (`speed-budget.md`).
