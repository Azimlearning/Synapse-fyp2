"""Run the Blueprint's expected behaviours against the assembled page in a real browser (blueprint.md section 5).

For each `BehaviourSpec` the changed variable is swept across its range through its control (the same input the keyboard fallback uses, which every handle drives), the
measured value is read from the readout that shows it, and `behaviour.holds` judges the pairs. Nothing is read from the writer's script: the page's own readouts are the
evidence. A behaviour that cannot be tested (no control with that name, no readout showing that quantity) is a failure with that reason, so a writer cannot pass by leaving
the thing out.

The Blueprint's variable names are the page's ids (the writer prompt says so): a control's id is a changed variable's name, and a measured variable is the name of the
formula or control a readout reads.
"""

from __future__ import annotations

import re

from playwright.sync_api import Page, sync_playwright

from api.blueprint.behaviour import BehaviourSpec, Verdict, holds
from api.buildscript.model import BuildScript

POINTS = 9
"""Samples across one sweep. Enough for a trend and a point value, few enough to keep a page's whole check in seconds."""

_SET = "([id, v]) => { var e = document.getElementById(id); e.value = String(v); e.dispatchEvent(new Event('input', {bubbles: true})); return parseFloat(e.value); }"


def _number(text: str) -> float | None:
    m = re.match(r"\s*(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)", text)
    return float(m.group(1)) if m else None


def _readout_for(bs: BuildScript, name: str) -> str | None:
    """The id of a readout that shows `name` (by its source), or None."""
    return next((r.id for r in bs.readouts if r.source == name), None)


def _samples(page: Page, bs: BuildScript, control_id: str, measured_readout: str) -> tuple[list[tuple[float, float]], str]:
    """(control value, readout value) over the control's range, with every other control at its start. The second item is a reason when a reading has no value."""
    c = next(c for c in bs.controls if c.id == control_id)
    for other in bs.controls:
        page.evaluate(_SET, [other.id, other.value])
    out: list[tuple[float, float]] = []
    for i in range(POINTS):
        actual = page.evaluate(_SET, [control_id, c.min + (c.max - c.min) * i / (POINTS - 1)])
        shown = _number(page.inner_text(f"#{measured_readout}"))
        if shown is None:
            return out, f"the readout '{measured_readout}' shows no value when {control_id} is {actual:g}"
        out.append((float(actual), shown))
    return out, ""


def sweep_page(html: str, bs: BuildScript, specs: list[BehaviourSpec]) -> list[tuple[BehaviourSpec, Verdict]]:
    """Judge every spec against the page. One browser for the whole list."""
    results: list[tuple[BehaviourSpec, Verdict]] = []
    controls = {c.id for c in bs.controls}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 360, "height": 900})
        page.set_content(html)
        for spec in specs:
            readout = _readout_for(bs, spec.measured)
            if readout is None:
                results.append((spec, Verdict(False, f"no readout shows '{spec.measured}' (a readout's source must be that name)")))
                continue
            if spec.kind == "stays-within":
                pts: list[tuple[float, float]] = []
                why = ""
                for cid in sorted(controls):
                    got, why = _samples(page, bs, cid, readout)
                    pts += got
                    if why:
                        break
                results.append((spec, Verdict(False, why) if why else holds(spec, pts)))
                continue
            if spec.variable not in controls:
                results.append((spec, Verdict(False, f"there is no control named '{spec.variable}' (a control's id must be the changed variable's name)")))
                continue
            pts, why = _samples(page, bs, spec.variable, readout)
            results.append((spec, Verdict(False, why) if why else holds(spec, pts)))
        browser.close()
    return results
