# Build Script: the writer's reply format

> Spec for V5-D02 and V5-D04. It extends v4's labelled sections (`free.v7`, D-81), which `free_house.py` already assembles. Argument names for Kit parts come from the Kit manifest (`packages/kit/dist/<version>/manifest.json`). The examples below are illustrative and are validated against the manifest at build time.

## 1. Goals

1. **Short.** Reuse Kit parts by name, so the reply is about 1,500 to 2,500 tokens (ESTIMATE) instead of v4's 4,000 to 6,000 for a whole page.
2. **Streamable.** Every unit (a section, or a line within PARTS, FORMULAS, CONTROLS and READOUTS) is complete on its own. A partial reply is all of its complete units.
3. **Checkable piece by piece.** Each unit can be validated when it arrives.
4. **The most checkable source first.** Numbers come from Kit science models, then FORMULAS that Synapse compiles, then model code when nothing else can express them (V5-D04).

## 2. Sections, in streaming order

The writer replies with these sections in this order. Each starts with its marker alone on a line. The order puts what the student can read first, and the code last.

| Marker | Required | Content | Shown while forming |
|---|---|---|---|
| `@@BASE` | no | The id of the stored environment it starts from, or `none` | "Building on: Hooke's law environment" |
| `@@TITLE` | yes | At most 60 characters | Yes |
| `@@KICKER` | yes | Field and level, for example `Physics, introductory` | Yes |
| `@@TRY` | yes | One sentence: what to drag or drop first | Yes |
| `@@PREDICT` | yes | A question, then `- choice` lines, then `Check: ...` | Yes, answerable |
| `@@IDEA` | yes | The law in plain words, then the formula | Yes |
| `@@STEPS` | yes | 3 or 4 `- step` lines | Yes |
| `@@PARTS` | yes | One Kit part per line (section 3) | As named chips |
| `@@CONTROLS` | no | Extra controls not provided by a Kit part, `id \| label \| min \| max \| step \| start \| unit` | As named chips |
| `@@FORMULAS` | no | One formula per line (section 5) | Shown as text in the Key idea card only after the reader passes |
| `@@READOUTS` | yes | `id \| label with unit \| source \| decimals` | As empty readout cards |
| `@@STYLE` | no | CSS for the model's drawing only, every selector under `#bench-art` | No |
| `@@DRAWING` | no | One `<svg id="bench-art">` for what no Kit scene draws | Sanitised inert picture |
| `@@SCRIPT` | no | Drawing, handles, motion and, when no Kit model or formula can express it, computation (section 6) | Never |
| `@@HINTS` | yes | 2 or 3 `- hint` lines | No (shown in the live environment) |
| `@@EXPLAIN` | yes | 2 or 3 short paragraphs | No |
| `@@TWISTS` | no | 2 or 3 `- twist` lines the student can tap to change the environment (`follow-ups.md`) | No (chips under the live environment) |
| `@@END` | yes | Nothing | Marks a complete reply |

## 3. PARTS lines

```
name = component { JSON arguments }
```

- `component` is a Kit manifest entry name (for example `planetGravity`, `hookes`, `massHanger`, `springScene`, `apparatus`, `graph`, `table`). It can also be a reviewed part from the parts library, written `saved.<part id>` (`caching.md` layer C3).
- Arguments are checked against that entry's signature: required fields, types, units, domains, and allowed apparatus kinds.
- A value written as `"$name"` refers to another part, control or formula by name. References must point backwards (the referenced name appears earlier) so each line can be validated on arrival.
- The rules from v4's plan checks apply where they fit: a model registered for the topic, units that match, ranges inside the model's domain, a scene scale the model can reach, known constants (PLAN-020).

## 4. CONTROLS and READOUTS lines

- **Controls:** as v4 `free.v7`. Each needs a handle in the drawing (`data-synapse-handle`) or comes from a Kit interaction part that already has one (v4 D-78, hands on every environment).
- **Readouts:** the `source` is a part or formula name. Synapse writes every readout. The model's script cannot write to a readout (section 6).

## 5. FORMULAS lines

```
name = expression [unit]
```

- **Allowed:** numbers; names of controls, parts and earlier formulas; `+ - * / ^` and a unary minus, parentheses; `sqrt`, `abs`, `min`, `max`, `exp`, `ln`, `log10`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan` (radians), `deg()`, `rad()`; the constants `pi`, `g_earth` (9.81), `c_light` and `avogadro` (the PLAN-020 values) and `G` (the SI value, ASSUMED, not in PLAN-020). `^` binds tighter than a unary minus and is right-associative (`-2^2` is `-4`, `2^3^2` is `512`).
- **Not allowed:** anything else (no function definitions, no conditionals in v5.0, no randomness, no time).
- **Units:** written in brackets after the expression. Checked by dimension where every named input carries a known unit, not by scale, and a bare constant stands the check down (V5-D24).
- **A value must exist everywhere.** A step with no finite value (division by zero, the log of a non-positive number, a root of a negative number, an overflow) is an error in both evaluators, at the step where it arises. The writer must choose ranges so none arises.
- **Compiled twice by Synapse:** to JavaScript for the page, and to a Python evaluator for the reference. The browser check compares every readout fed by a formula with the Python value across each control's range, as v4 does for Kit models (L3).
- **What this proves, and what it does not.** It proves the page computes what the formula says. It does not prove the formula is right: the second reader reads every formula, and the environment's label stays `model-checked`.

## 6. SCRIPT: anything the sandbox allows

Kit parts and formulas are preferred because they are checked more deeply. They are **not required** (V5-D16). The script may:

- draw with SVG or canvas;
- simulate in time steps;
- handle collisions and particles;
- compute with loops and conditions;
- use vetted libraries served from `/vendor/`.

An environment may be all script when nothing else fits. The script gets a small API from the house frame:

| Call | Does |
|---|---|
| `host.value(name)` | The current value of a control, part or formula |
| `host.on(name, fn)` | Calls `fn(value)` when it changes |
| `host.set(control, value)` | Sets a control from a handle drag (snapped to its step, dispatches `input`) |
| `host.found(text)` | Sets the "What you found" line |
| `host.reducedMotion` | True when motion must be still |

| `host.readout(id, value)` | Feeds a readout from script computation, for numbers no Kit model or formula can express. The readout is marked "computed by model code" and tested against the Blueprint's expected behaviour |

**Readouts fed from script:** a READOUTS line whose source is `script` is fed only through `host.readout`. The validator refuses a `host.readout` call for any other readout, and a `script` readout the script never feeds.

**Refused:** writing to a readout element directly (use `host.readout`); any v4 scan-refused API (network, storage, `eval`, timers given strings, navigation, `postMessage`, `parent`, `top`); a number shown in text that no control or formula backs (v4's provenance audit). The drawing must follow values only through `host.on`, so a picture cannot disagree with the readouts.

## 7. A complete example

Question: *"Hooke's law, but two springs in series on Mars."*

```
@@BASE
hookes_spring
@@TITLE
Two springs in series on Mars
@@KICKER
Physics, introductory
@@TRY
Drag a mass from the tray onto the hanger under the two springs.
@@PREDICT
On Mars, will the same mass stretch the two springs more or less than on Earth?
- More
- Less
- The same
Check: hang 200 g on Earth, then switch the planet to Mars.
@@IDEA
Two springs in series share the same pull, so they stretch more than one spring.
k_total = 1 / (1/k1 + 1/k2), and extension = W / k_total, with W = m g.
@@STEPS
- Hang 200 g and read the extension on Earth.
- Drag the planet chip to Mars and read it again.
- Make spring 2 stiffer and watch the total stretch fall.
@@PARTS
planet = planetPicker {"start": "earth"}
g = planetGravity {"planet": "$planet"}
bench = massHanger {"masses_g": [50, 100, 200], "start_g": 0}
W = weight {"m": "$bench", "g": "$g"}
@@CONTROLS
k1 | Spring 1 stiffness | 10 | 50 | 5 | 20 | N/m
k2 | Spring 2 stiffness | 10 | 50 | 5 | 20 | N/m
@@FORMULAS
k_total = 1 / (1 / k1 + 1 / k2) [N/m]
x = W / k_total [m]
@@READOUTS
r_g | Gravity here (N/kg) | g | 2
r_W | Weight (N) | W | 2
r_k | Combined stiffness (N/m) | k_total | 1
r_x | Total extension (m) | x | 3
@@DRAWING
<svg id="bench-art" viewBox="0 0 320 360" role="img" aria-label="Two springs in series">...</svg>
@@SCRIPT
var NS = document.getElementById("bench-art").namespaceURI;
host.on("x", function (x) { /* stretch both drawn springs in proportion to their share */ });
/* two drag handles for k1 and k2 call host.set("k1", value) */
@@HINTS
- In series, each spring feels the whole weight.
- Mars pulls with about 3.7 N/kg.
@@EXPLAIN
...
@@END
```

The lane is Free (it has FORMULAS and a model drawing), so the label is `model-checked`. The badges show `planetGravity` and `weight` as Kit science models (source checked where cited), and `k_total` and `x` as model-written formulas, read by the second reader and recomputed independently.

## 8. Patch replies (change this environment)

For a follow-up, the writer replies with `@@PATCH` and only the sections it changes. A PARTS, CONTROLS, FORMULAS or READOUTS line replaces the line with the same name, and `name = delete` removes one. See `follow-ups.md`.

## 9. Validation summary (per unit, on arrival)

| Unit | Checks | On failure |
|---|---|---|
| Text sections | Plain text, lengths, no markup, no long dashes | Stop, retry with reason |
| PARTS line | Known component, signature, units, domain, backward references | Stop, retry with reason |
| CONTROLS line | Ids, ranges, step, unit | Stop, retry with reason |
| FORMULAS line | Grammar, names known, units consistent where known | Stop, retry with reason |
| READOUTS line | Source exists, unit stated | Stop, retry with reason |
| STYLE, DRAWING | Selector scope, v4 scan rules, size limit for the reader | Stop, retry with reason |
| SCRIPT | v4 scan rules, the API rules above, length within the reader's limit | Stop, retry with reason |
| Whole reply | Every control has a handle; every readout has a source; `@@END` present | Retry with reason |

## 10. Filling the space (V5-D23)

The writer must size the drawing to its container: it uses a viewBox that matches the bench's shape and scales the apparatus to fill at least 55 percent of the bench's width and 50 percent of its height. It must not place a small drawing in a corner or leave a region of the bench empty. The house frame places the panels so no column is left empty. The browser's fill check refuses an Environment that fails, and the reason goes back to the writer once.

## 11. What the V5-2 prototype builds, and what it leaves for V5-3 (2026-11-17)

- **`@@PARTS` is `none`, and `@@BASE` is `none`.** The parser and the validator read PARTS lines (a Kit part that exists, its arguments from its signature, backward references, a science model's domain) so the format is ready, but Kit parts are not mounted in the assembled page until V5-3 builds the part host, so the assembler refuses a script that lists any. For the same reason a stored Environment is not used as a base yet. The writer is told to write the part's law as a formula.
- **Names.** The id of each control is the name of a Blueprint variable whose role is `changed`, and each `measured` variable is the name of a formula or control that a readout shows (V5-D25).
- **The reply is validated whole.** The units are ready to be checked as they stream (a test proves no prefix of a good reply yields a finding), and the pipeline streams in V5-3.
- **Rule ids** are `BS-000` to `BS-008` (see `api/buildscript/validate.py`): reply, text, parts, controls, formulas, readouts, style and drawing, script, whole reply.
- **The five fixtures** (`api/buildscript/fixtures/*.txt`) are complete hand-written replies that pass every check and the real browser; one of them is the worked example shown to the writer.
