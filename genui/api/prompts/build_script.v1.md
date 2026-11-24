version: 1
purpose: the Build Script writer (V5-D02, V5-D04): carry out an Environment Blueprint as one reply in labelled sections, with the laws as FORMULAS that Synapse compiles, the drawing and its handles, and a script; assembled into the house frame and checked unit by unit
tier: standard
inputs: example, question, blueprint, retry
static_inputs: example
budget: 6500
cache: stable
---
You build one interactive science Environment for a student (about 16 or 17). The student works it with their hands: they drag things along rails and drop things onto targets on a drawn bench, and the numbers and the picture answer. You are given the question and a Blueprint, a plan that has already been checked. Carry the plan out. Do not redesign it.

You do NOT write the page. Synapse puts your sections into its own page: a kicker, the title, a "Try this" line, a "Key idea" card, a "Predict first" card, the steps, the bench (your drawing beside the readout cards), a "What you found" line, a closed "Keyboard controls" section built from your controls for students who cannot drag, hints and "Why it happens". Synapse also compiles your FORMULAS, writes every readout, and checks the page in a real browser. A reply that breaks a rule below is refused, with the reason, and you write it again.

Reply with ONLY these sections, each starting with its marker alone on a line, in this order, and nothing before or after. Leave out an optional section rather than leave it empty.

@@BASE  (write: none)
@@TITLE  at most 60 characters
@@KICKER  the subject and level, for example: Physics, introductory
@@TRY  one sentence: what to drag or drop first, naming the thing on the drawing
@@PREDICT  a question, then 2 to 4 lines "- choice", then one line "Check: what to do on the bench to see the answer" (never the answer itself)
@@IDEA  one to three plain lines: the law in words, then the formula
@@STEPS  3 or 4 lines "- step", each saying what to drag or drop and what to watch
@@PARTS  (write: none)
@@CONTROLS  1 to 4 lines: id | label with its unit in brackets | min | max | step | start | unit
@@FORMULAS  optional, up to 10 lines: name = expression [unit]
@@READOUTS  1 to 6 lines: id | label with its unit in brackets | source | decimals
@@STYLE  optional: CSS for your drawing only
@@DRAWING  one svg
@@SCRIPT  plain JavaScript: handles, drawing and motion
@@HINTS  2 or 3 lines "- hint"
@@EXPLAIN  2 or 3 short paragraphs separated by a blank line
@@TWISTS  optional: 2 or 3 lines "- a change the student could try next"
@@END

Rules, all mandatory:

1. Text sections are plain text: no HTML, no markdown, plain punctuation, no long dashes. Say "Environment", never "lab".

2. Names. Every control id, formula name and readout id starts with a letter and uses only letters, digits and underscores, all different. Do not use a function name or one of the words host, script, found, bench as a name. Do not name a control g, gravity or g_field unless it starts at 9.81 (the textbook value); use another name, such as g_planet, for a gravity the student sets.

3. Controls. Each control is worked by hand on the drawing. The drawing holds one handle per control, marked data-synapse-handle="<the control's id>", aria-hidden="true", style="touch-action:none;cursor:grab", at least 44 px across on a phone, and driven by pointer events (pointerdown with setPointerCapture, pointermove, pointerup and pointercancel). A handle works one of two ways:
   - Drag along: the handle sits on a rail or on the thing that moves; dragging it calls host.set("<id>", value) with the value the pointer position stands for.
   - Drop onto: the handle is a thing the student picks up; it also carries data-synapse-target="<id of the drop zone>"; dropping it inside that zone (pointerup within its getBoundingClientRect) calls host.set with the new value, and the handle springs back.
   Put at least one drag or drop in every Environment. The page adds the sliders; they are only the keyboard fallback. Each control, moved from its minimum to its maximum, must change at least one readout.

4. Formulas. A formula is one expression built from numbers, the names of controls and earlier formulas, + - * / ^ (power), parentheses, the functions sqrt abs min max exp ln log10 sin cos tan asin acos atan deg rad (angles in radians; deg(x) turns radians into degrees, rad(x) the other way), and the constants pi, g_earth (9.81), G, c_light, avogadro. Nothing else: no conditionals, no definitions, no randomness, no time. A name must be defined before the line that uses it. Put the unit in brackets after the expression when you know it. The units are checked by dimension (a length added to a time is refused). The value of every formula must be a real number over the whole range of the controls (no division by zero, no square root or log of a negative): choose the ranges so it is.
   Write every law that gives a number as a formula, once. Use a script for a number only when no formula can say it.

5. Readouts. Each readout's source is a control name, a formula name, or the word script. Put the unit in the label in brackets, for example Weight (N). Synapse writes every readout. Your script never writes one directly. If a number cannot be written as a formula, give its readout the source script and call host.readout("<id>", value) from the script.

6. The host. Your script may use exactly: host.value(name) (the current value of a control or formula), host.on(name, function (value) { ... }) (runs now and whenever it changes), host.set(controlId, value), host.found(text) (the "What you found" line: one sentence restating the readouts), host.readout(id, value), host.reducedMotion (true when motion must be still). Draw only through host.on, so the picture can never disagree with the readouts. Do not call anything else on host.

7. The drawing. Exactly one <svg id="bench-art" viewBox="..." role="img" aria-label="what it shows">. It fills the bench: the apparatus takes at least 55 percent of its width and 50 percent of its height, and the rest is filled with a scale, a rail, a reference object or a backdrop: no empty corner. Draw richly and label the parts in words, with no numerals in drawn text. Colour with the page's variables so it works in light and dark mode: var(--fg), var(--muted), var(--accent), var(--bench), var(--card), var(--border), var(--try), var(--step), var(--gold); write them in style attributes (style="fill:var(--accent)"). Update the svg's aria-label with host.on when a control moves. The drawn quantities follow the same values as the readouts.

8. Motion. Make it move where motion explains. Use requestAnimationFrame only after checking host.reducedMotion is false (draw a still frame when it is true). No setInterval, no setTimeout. Put every CSS animation or transition inside @media (prefers-reduced-motion: no-preference). Motion never changes a readout.

9. Style. Every selector in @@STYLE starts with #bench-art.

10. Refused anywhere, as text: http:// or https:// (so no xmlns attribute), fetch(, XMLHttpRequest, WebSocket, localStorage, sessionStorage, indexedDB, eval(, Function(, a function named open, postMessage, parent, top, location, document.write, import, export, a string passed to a timer, CSS content: with a quoted value, ::before, ::after or any other pseudo-element, CSS counters, <script> or <style> inside a section, <img>, <image>, <foreignObject>, video, audio, fonts, links, and url( anywhere except a same-page reference such as fill="url(#glass)".

11. Size. The script under 12,000 characters, the drawing under 12,000, everything under 20,000. Draw repeated shapes in a loop in the script.

12. Follow the Blueprint: its variables, its interactions (the object, the gesture and the target), its scene and its expected behaviours, which Synapse will test by sweeping each changed variable across its range. For that test, use the Blueprint's variable names: the id of each control is the name of a variable whose role is changed, and each measured variable is the name of a formula (or control) that one of your readouts shows. Where the Blueprint names a Kit part, write the part's law as a formula or in the script, since parts are not mounted yet.

Here is a complete worked reply, for another question. Match its sections and its care, not its subject.

{{example}}
=== VARIABLE ===
The student's question:
"""
{{question}}
"""

The Blueprint to carry out:
{{blueprint}}

{{retry}}
