# Visual design in v5

> From looking at v4's environments at 1280 and 360 px (2026-11-01). Motion, dragging and dark mode were not reviewed then, so the first V5-6 task is a full review including them. The visual standard stays Synapse V3's (owner's call, v4 D-38) and v4's demo benches (v4 D-80).

## 1. What was found

| Finding | Evidence |
|---|---|
| Generated environments put four text cards above the bench | Bench at 575 px on desktop; 1,162 to 1,242 px on a 740 px phone screen (the third screen). Kit environments: 268 to 360 px and 612 to 860 px (MEASURED) |
| Generated drawings are unreadable on a phone | The SVG scales to about 300 px wide, so labels shrink below legible size (LOOKED AT) |
| Labels collide | Pendulum ticks run together; a line through "0.10 kg"; planets bench "Jupiter" over the axis title, Saturn's ring touching Jupiter |
| Two design languages | Kit environments: gold serif title and step chips. Generated environments: sans title and stacked cards |
| Flat backdrops | v4 `free.v7` rule 5 steers backgrounds to the light bench colour, so a black hole sits on near-white. The Kit's dark planets scene shows the difference a backdrop makes |
| Sparse benches | Apparatus small inside a large empty card |
| No shared fonts in the frame | Environments fall back to system fonts |

## 2. Rules for v5

**Layout: bench first (one house frame for Kit and generated environments).**

```
[kicker]            Physics, introductory
[title]             Two springs in series on Mars
[try this]          Drag a mass from the tray onto the hanger.
[PREDICT strip]     one line + choices (collapses after answering)
[BENCH | READOUTS]  desktop: side by side; phone: bench, then a 2-column readout grid
[what you found]
[steps]             folded, opens to a numbered list
[key idea]          folded on phone, open on desktop
[hints]             one at a time
[why it happens]
[keyboard controls] folded
```

On a phone, the bench must start on the first screen.

**Drawing:**

| Rule | Detail |
|---|---|
| Backdrop by subject | Space and astronomy: deep navy with stars. Chemistry: the environment bench with glassware. Biology: a soft cell or tissue tone. Circuits: a board. Each a theme token in the frame, light and dark |
| Size | The drawing fills its column. Apparatus at least 60 percent of the drawing's height |
| Text | At least 11 px when rendered at 360 px; at most 4 words per label; leader lines instead of crowding |
| Handles | At least 44 px, a visible grip, a cursor and a focus ring |
| Motion | Where motion explains (bubbles, falling, flow); still under reduced motion (v4 rules) |
| Colour | Kit tokens; real colours allowed for liquids, flames, planets |
| Same-document gradients | Allowed (`fill="url(#glass)"`), as in v4 |

**One design language.**
- The Kit's tokens and type scale apply to every environment.
- Fonts (V3's Fredoka and Nunito) are vendored under `/vendor/fonts/` and allowed by the CSP's `font-src` for our own origin only (hard constraint 2 still holds: no runtime CDN).
- This is a Kit change, so it needs a relock.

**Forming environment = live environment layout.** The draft uses the same frame, so the swap does not jump (`streaming-and-draft.md`).

## 3. Checks that enforce it

Layout checks in the verifier (`verification.md` section 4): collisions, overflow, minimum text and handle size, bench on the first phone screen, contrast. They apply to every environment, Kit or generated.

## 4. Acceptance (V5-6 exit)

- Screenshots of 10 generated environments and 5 Kit environments at 360 and 1280 px, light and dark, looked at by the owner. **8 of 10 generated environments judged "same product as the Kit environments"** (TARGET, `synapse-v5-PRD.md` G8).
- Layout checks pass on 100 percent of delivered environments.
- A real-phone pass (v4 deploy-gate item).

## 5. Filling the space: no empty or big white spaces (V5-D23)

**Finding (2026-11-14, from the owner's screenshot of the stored Wave speed Environment, 1920 px wide):**
- the bench card is about 660 px wide with a 120 px wave picture in its left corner;
- the right column holds readouts and a graph;
- the area under the bench, left of the graph, is empty;
- the Environment frame's right side is also unused.

**Rules for the house frame (Kit and generated):**

| Rule | Detail |
|---|---|
| Apparatus scales to the bench | The drawing's viewBox fits its container: the apparatus fills at least 55 percent of the bench's width and 50 percent of its height, and grows on a wide screen up to a cap (not a fixed small size) |
| Reflow, not columns | The frame is a grid that places the bench, readouts, graph and table so each row is full. On a wide screen the graph and table sit beside or under the bench in the free space, never leaving a dead strip under a short block. On a phone everything stacks at full width |
| Row heights follow content | A row is as tall as its tallest block, and shorter blocks stretch to match (or the next block moves up) instead of leaving a gap |
| No spacers | Empty `div`s, fixed-height placeholders and blank margins beyond the frame's spacing tokens are refused by the scan |
| Wide screens use width | Above 1280 px the Environment may take a three-zone layout (bench, readouts and graph, steps and hints) rather than centring a narrow column in a wide frame |
| Short content fills with something useful | A bench with little to draw adds a scale, a reference object or a labelled axis (from the Blueprint's `scene`), not blank space |
| Backdrop | The bench always has a themed backdrop, so an unused area reads as scene, not as a hole (rule in section 2) |

**Checked by** the fill check in `verification.md` section 4a, at 360, 768, 1280 and 1920 px.

**Acceptance (V5-6 exit, added):** the fill check passes on 100 percent of delivered Environments, its thresholds are calibrated and the detection rate on planted empty-space defects is reported, and the owner's Wave speed screenshot no longer shows an empty area at 1920 px.
