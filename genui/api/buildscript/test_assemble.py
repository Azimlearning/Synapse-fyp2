"""Assembling a Build Script into a page: what the page contains, that it passes the static scans, and that the references the browser will compare with are right."""

from __future__ import annotations

import re

import pytest

from api import postprocess
from api.buildscript import formula as fm
from api.buildscript.assemble import AssembleError, assemble, prelude, readout_unit, reference_values
from api.buildscript.conftest import PAIRS, script_text
from api.buildscript.parse import parse
from api.verify.scan import forbidden_api_scan, free_lane_scan

NAMES = list(PAIRS)
ORIGIN = "http://localhost:3000"


def built(name: str):  # noqa: ANN201
    bs = parse(script_text(name))
    assert not isinstance(bs, str), bs
    return bs


@pytest.mark.parametrize("name", NAMES)
def test_every_fixture_assembles_into_a_page_that_passes_the_static_scans(name: str) -> None:
    html = assemble(built(name))
    assert forbidden_api_scan(html) is None and free_lane_scan(html) is None
    assert not isinstance(postprocess.run(html, public_origin=ORIGIN), postprocess.PostprocessReject)
    assert html.count("<script>") == 1 and "<script src" not in html
    assert "host.start();" in html and "var host = (function ()" in html


def test_the_page_carries_the_house_frame_and_the_writers_words_escaped() -> None:
    bs = built("springs_series_planet")
    html = assemble(bs)
    for part in ("Try this:", "Key idea", "Predict first", "Steps", "Keyboard controls", "Need a hint?", "Why it happens", 'id="found"'):
        assert part in html, part
    for c in bs.controls:
        assert f'data-synapse-control="{c.id}"' in html and f'for="{c.id}"' in html
    for r in bs.readouts:
        assert f'data-synapse-readout="{r.id}"' in html


def test_every_formula_is_compiled_into_the_page_in_order() -> None:
    bs = built("springs_series_planet")
    js = prelude(bs)
    positions = [js.index(f'["{f.name}", function (V)') for f in bs.formulas]
    assert positions == sorted(positions)
    assert fm.JS_HELPERS in js and "V.mass_g" not in js.split("var FORMULAS")[0]


def test_a_label_cannot_close_the_script_element() -> None:
    bs = built("springs_series_planet")
    evil = bs.readouts[0].__class__(bs.readouts[0].id, "Weight (</script><b>)", bs.readouts[0].source, 2)
    from dataclasses import replace

    js = prelude(replace(bs, readouts=[evil, *bs.readouts[1:]]))
    assert "</script>" not in js and "<\\/script>" in js


def test_the_readout_unit_is_the_last_parenthesised_text_of_its_label() -> None:
    assert readout_unit("Weight (N)") == "N" and readout_unit("Speed (m/s)") == "m/s"
    assert readout_unit("pH of the flask") == "" and readout_unit("Size (times)") == "times"
    assert readout_unit("Gravity (N/kg) here") == ""


def test_parts_are_not_mounted_in_this_build() -> None:
    from dataclasses import replace

    from api.buildscript.model import PartLine

    bs = built("springs_series_planet")
    with pytest.raises(AssembleError, match="V5-3"):
        assemble(replace(bs, parts=[PartLine("g", "planetGravity", {"planet": 3})]))


def test_a_script_without_a_drawing_or_controls_is_not_assembled() -> None:
    from dataclasses import replace

    bs = built("springs_series_planet")
    for broken in (replace(bs, drawing=""), replace(bs, controls=[]), replace(bs, readouts=[])):
        with pytest.raises(AssembleError):
            assemble(broken)


# ── the Python reference the browser compares with ──────────────────────────────────────────────────────────────────────────
def test_reference_values_for_the_springs() -> None:
    bs = built("springs_series_planet")
    ref = reference_values(bs, {"mass_g": 100, "g_planet": 3.5, "k1": 20, "k2": 30})
    assert ref["mass"] == pytest.approx(0.1) and ref["weight"] == pytest.approx(0.35)
    assert ref["k_total"] == pytest.approx(12.0) and ref["x"] == pytest.approx(0.35 / 12.0) and ref["x_cm"] == pytest.approx(100 * 0.35 / 12.0)


def test_reference_values_for_the_pendulum_and_the_lens() -> None:
    import math

    ref = reference_values(built("pendulum_planet"), {"length": 1.0, "start_angle": 15, "g_planet": 9.81})
    assert ref["period"] == pytest.approx(2 * math.pi * math.sqrt(1 / 9.81)) and ref["freq"] == pytest.approx(1 / ref["period"])
    ref = reference_values(built("lens_image"), {"object_dist": 40, "focal": 10})
    assert ref["image_dist"] == pytest.approx(40 * 10 / 30) and ref["magnification"] == pytest.approx(1 / 3)


def test_a_value_with_no_value_is_an_error_in_the_reference() -> None:
    with pytest.raises(fm.FormulaError):
        reference_values(built("lens_image"), {"object_dist": 10, "focal": 10})


def test_no_long_dashes_in_the_generated_prelude() -> None:
    for name in NAMES:
        js = prelude(built(name))
        assert not re.search("[–—]", js)
