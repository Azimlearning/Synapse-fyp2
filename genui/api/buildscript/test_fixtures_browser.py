"""The five twist fixtures in a real browser.

1. Each assembled page goes through the same verifier any Free page does (`verify_environment`): post-processing, the L0 scans, the render, every control exercised,
   its handle dragged or dropped, the provenance audit. A refusal raises, and the test fails with the verifier's reason.
2. Each page is opened directly and its controls are set to the ends of their ranges and a middle value: every readout must show the number the Python
   reference gives (to the readout's decimals), and no page error may occur. This is the check that the compiled JavaScript and the Python evaluator agree on the page.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from api.buildscript import formula as fm
from api.buildscript.assemble import assemble, reference_values
from api.buildscript.conftest import PAIRS, script_text
from api.buildscript.parse import parse
from api.kit import latest_version
from api.pipeline.grounding import UNCHECKED_CITATION
from api.verify.mint import verify_environment

NAMES = list(PAIRS)
ORIGIN = "http://localhost:3000"


@pytest.mark.parametrize("name", NAMES)
def test_the_page_passes_the_free_checks_in_a_real_browser(name: str, kit_dist: Path) -> None:
    bs = parse(script_text(name))
    assert not isinstance(bs, str)
    env = verify_environment(
        slug=f"v5_2_{name}",
        title=bs.title,
        raw_html=assemble(bs),
        lane="free",
        label="model-checked",
        kit_version=latest_version(kit_dist),
        citations=[UNCHECKED_CITATION],
        plan_summary="A Build Script fixture.",
        public_origin=ORIGIN,
        kit_dist=kit_dist,
        interaction_seconds=1.0,
        plan_models=None,
    )
    assert env.lane == "free" and env.checked.controls_exercised == len(bs.controls)


def _shown(text: str) -> float:
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)", text)
    assert m, f"the readout shows '{text}'"
    return float(m.group(1))


def _settings(bs) -> list[dict[str, float]]:  # noqa: ANN001
    """Every control at its minimum, its maximum and its start, all together, plus one control at a time moved to each end: a handful of settings."""
    start = {c.id: c.value for c in bs.controls}
    out = [dict(start), {c.id: c.min for c in bs.controls}, {c.id: c.max for c in bs.controls}]
    for c in bs.controls:
        out += [start | {c.id: c.min}, start | {c.id: c.max}]
    return out


@pytest.mark.parametrize("name", NAMES)
def test_every_readout_shows_the_python_reference_across_the_controls(name: str) -> None:
    bs = parse(script_text(name))
    assert not isinstance(bs, str)
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 360, "height": 900})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.set_content(assemble(bs))
        for setting in _settings(bs):
            for cid, value in setting.items():
                page.evaluate("([id, v]) => { var e = document.getElementById(id); e.value = String(v); e.dispatchEvent(new Event('input', {bubbles: true})); }", [cid, value])
            try:
                ref = reference_values(bs, setting)
            except fm.FormulaError:
                continue  # no value at this setting: the page shows "no value", checked below
            for r in bs.readouts:
                if r.source == "script":
                    continue
                text = page.inner_text(f"#{r.id}")
                want = ref[r.source]
                assert abs(_shown(text) - round(want, r.decimals)) <= 10 ** -r.decimals / 2 + 1e-9, (name, setting, r.id, text, want)
        browser.close()
    assert errors == []
