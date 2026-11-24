"""The Blueprint's expected behaviours, run against each fixture page in a real browser: the page's own readouts must show every stated relation."""

from __future__ import annotations

import json

import pytest

from api.blueprint.behaviour import compile_behaviours
from api.buildscript.assemble import assemble
from api.buildscript.conftest import BLUEPRINTS, PAIRS, script_text
from api.buildscript.parse import parse
from api.buildscript.sweep import sweep_page
from api.schema.generated import Blueprint


@pytest.mark.parametrize("name", list(PAIRS))
def test_every_expected_behaviour_holds_on_the_page(name: str) -> None:
    bp = Blueprint.model_validate(json.loads((BLUEPRINTS / f"{PAIRS[name]}.json").read_text(encoding="utf-8")))
    bs = parse(script_text(name))
    assert not isinstance(bs, str)
    specs = compile_behaviours(bp)
    results = sweep_page(assemble(bs), bs, specs)
    assert len(results) == len(specs) >= 2
    failed = [(s.text, v.reason) for s, v in results if not v.ok]
    assert failed == []


def test_a_behaviour_the_page_cannot_show_is_a_failure_with_a_reason() -> None:
    bp = Blueprint.model_validate(json.loads((BLUEPRINTS / "good_lens_image.json").read_text(encoding="utf-8")))
    bs = parse(script_text("lens_image"))
    assert not isinstance(bs, str)
    specs = compile_behaviours(bp)
    bad = [specs[0].__class__(**{**specs[0].__dict__, "measured": "nothing_shows_this"}), specs[0].__class__(**{**specs[0].__dict__, "variable": "no_such_control"})]
    (a, va), (b, vb) = sweep_page(assemble(bs), bs, bad)
    assert not va.ok and "no readout shows" in va.reason
    assert not vb.ok and "no control named" in vb.reason


def test_a_page_whose_readout_shows_the_wrong_trend_fails_the_behaviour() -> None:
    bp = Blueprint.model_validate(json.loads((BLUEPRINTS / "good_lens_image.json").read_text(encoding="utf-8")))
    bs = parse(script_text("lens_image"))
    assert not isinstance(bs, str)
    flipped = bs.__class__(**{**bs.__dict__, "formulas": [f.__class__(f.name, "object_dist + focal" if f.name == "image_dist" else f.expr, f.unit) for f in bs.formulas]})
    results = sweep_page(assemble(flipped), flipped, compile_behaviours(bp))
    assert any(not v.ok for _, v in results)
