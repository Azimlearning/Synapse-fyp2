# Verification in v5: faster, never weaker

> v4's verifier is kept whole (`../../Synapse-V4/api/verify/`). This lists what v5 adds and moves. Every change is accepted only if the L6 planted-defect detection rate stays at or above v4's, measured and reported (v4 hard constraint 9).

## 1. Kept from v4

- L0 scan and post-processing.
- L1 Kit provenance audit.
- L2 browser run: every control swept, every handle dragged by mouse, key and finger.
- L3 independent reference values for Kit science models.
- L4 second reader.
- Accessibility checks.
- Grounding against the corpus.
- Mint, gate, browser re-hash.
- Hostile set and L6 suite.

## 2. Checks while streaming (new)

Each Build Script unit is checked on arrival (`build-script.md` section 9). A failure cancels the reply at once. In v4 the "too long" check ran after 100 to 174 s of writing (MEASURED). In v5 a script over the reader's limit is stopped at the character where it crosses it.

The early stop also covers:

- any v4 scan-refused pattern;
- an unknown Kit part;
- a unit mismatch;
- a control without a handle (checked when `@@SCRIPT` closes).

## 3. Formula recomputation (new, V5-D04)

1. Synapse compiles each `@@FORMULAS` line to JavaScript for the page and to a Python evaluator.
2. The browser run sweeps each control across its grid and reads every formula-fed readout.
3. Python evaluates the same formula at the same inputs.
4. Any difference beyond the readout's rounding refuses the environment.

**What it proves:** the page shows what the formula says, and the model's script cannot change a readout. **What it does not prove:** that the formula is right. The second reader reads every formula, and the label stays `model-checked`.

New L6 rows:

- a script that writes to a readout;
- a formula compiled correctly but displayed with the wrong unit;
- a drawing that disagrees with the formula, for example a spring drawn shorter while the extension readout grows (checked through `host.on` traces).

## 4. Layout checks (new, V5-D10)

Run in the browser at 360 px and 1280 px, light and dark:

| Check | Refuses when |
|---|---|
| Text collision | Two text boxes in the drawing overlap by more than a few pixels |
| Overflow | Text or a handle lies outside the drawing's visible box |
| Minimum size | Rendered drawing text under 11 px at 360 px, or a handle under 44 px |
| Bench position | The drawing starts below the first screen at 360 px (house frame rule) |
| Contrast | Drawing text below WCAG AA against its backdrop |

A failure feeds the normal retry with the reason ("the labels '30°' and '20°' overlap at 360 px"). These checks run on Kit environments too: v4's planets bench has a collision ("Jupiter" over the axis title).

## 5. Faster runs (V5-D09)

| Change | Expected saving | Accepted only if |
|---|---|---|
| Virtual clock: Playwright's `page.clock` fakes `Date`, `setTimeout`, `setInterval`, `requestAnimationFrame` and `performance`, so v4's fixed 10 s interaction window runs in virtual time | Most of the 10 s (ESTIMATE); virtual time can also run much longer, which may catch the listed `g-timer-60s-forge` miss | L6 rate not lower; drag tests still use real pointer events |
| Warm browser per worker, fresh context per environment | Chromium start per environment (to be measured) | Contexts share nothing; the hostile set still passes |
| Second reader and browser run in parallel | About 2 to 6 s (the reader's measured time) | Either refusing refuses the environment |
| Verification result cache (`caching.md` C6) | A whole run for an identical page | Same HTML hash and Kit hash and verifier version; the gate still re-checks |

## 6. Per-part provenance (new)

Every environment records, for each part, what it earned. The Provenance panel lists them:

| Part kind | Badge | Earned by |
|---|---|---|
| Kit science model with a proved citation | Source checked | v4 grounding |
| Kit science model without a citation | Kit checked | Kit registration suite and L3 |
| Kit interaction or scene | Kit part | Kit audit |
| Formula | Written by the model, recomputed | Formula recomputation plus the second reader |
| Drawing or script | Written by the model, browser checked | L0, L2, layout checks plus the second reader |

The environment's overall label is still the lowest it can honestly carry (v4 hard constraint 3).

## 7. Later

- **Design reader:** a small vision model scores a screenshot for clarity, usefulness and completeness, the criteria OpenAI reports grading its generated interfaces on. It is used only to trigger a retry and is reported, never the primary metric.
- **Supervised attack pass** (v4 `guardian_pass.md`) on the new Build Script surface before any public deploy.

## 4a. Fill check: no empty or big white spaces (new, V5-D23)

The owner's example (2026-11-14, a stored v4 Kit Environment, LOOKED AT on a 1920 px screen): in the Wave speed Environment the bench card is about 660 px wide, but the wave picture inside it is about 120 px wide, and the area under the bench, left of the graph, is empty for more than 250 px.

**Measured in the browser** at 360, 768, 1280 and 1920 px, light and dark, once the Environment is ready and again after the control sweep:

| Measure | How | Refuses when (ASSUMED, to calibrate) |
|---|---|---|
| Bench fill | The drawn content's bounding box (every SVG shape, canvas pixels that differ from the backdrop, drawn elements) compared with the bench container | Content covers less than 55 percent of the container's width, or less than 50 percent of its height |
| Largest empty rectangle | Screenshot of the Environment frame, background colour found by sampling, largest axis-aligned rectangle of background-only pixels (a standard maximal-rectangle scan on a downsampled image) | The rectangle is more than 20 percent of the frame's area, or its sides both exceed 240 px |
| Dead column | The tallest empty strip beside a block narrower than its row | More than 160 px tall and more than 30 percent of the row's width |
| Blank band | A full-width horizontal band with no content between two blocks | More than 80 px |
| Content area | Total drawn content area compared with the viewport at 1280 px | Under 35 percent |

A failure feeds the normal retry with the reason ("the bench is 70 percent empty at 1280 px: make the apparatus larger", "a 280 px empty area beside the graph: move the graph next to the bench"). Intended whitespace is allowed through margins and gutters at the house frame's fixed sizes only.

**Calibration (V5-6).** Run the check on every stored Environment (31 library, the Free ones) and on planted defects (a tiny drawing, a hidden panel, a 400 px spacer). Set thresholds so every planted defect is refused and the Environments the owner judges "filled" pass. Report both rates. This is the same discipline as L6: the detection rate is reported, not assumed.

**Kit Environments too.** The check runs on Kit labs, so scenes that fail (a small wave picture in a wide card) become Kit changes with a relock.
