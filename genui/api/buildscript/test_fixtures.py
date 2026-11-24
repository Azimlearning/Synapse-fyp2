"""The five twist fixtures: each is a Build Script that parses, validates and assembles, and is built from a Blueprint that passes its own checks.

The browser half (the page in a real Chromium, every readout against the Python reference) is `test_fixtures_browser.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api import kitmanifest
from api.blueprint.checks import check
from api.buildscript.assemble import assemble
from api.buildscript.conftest import BLUEPRINTS, FIXTURES, PAIRS, script_text
from api.buildscript.parse import parse
from api.buildscript.validate import validate
from api.schema.generated import Blueprint

NAMES = list(PAIRS)


def test_there_are_five_twist_fixtures_and_each_has_a_blueprint() -> None:
    assert sorted(p.stem for p in FIXTURES.glob("*.txt")) == sorted(NAMES)
    for bp in PAIRS.values():
        assert (BLUEPRINTS / f"{bp}.json").is_file()


@pytest.mark.parametrize("name", NAMES)
def test_the_blueprint_passes_and_the_script_parses_validates_and_assembles(name: str, manifest: kitmanifest.Manifest) -> None:
    blueprint = Blueprint.model_validate(json.loads((BLUEPRINTS / f"{PAIRS[name]}.json").read_text(encoding="utf-8")))
    assert check(blueprint, manifest) == []
    raw = script_text(name)
    assert validate(raw, manifest, early_stop=False) == []
    bs = parse(raw)
    assert not isinstance(bs, str)
    assert "<svg" in assemble(bs)


@pytest.mark.parametrize("name", NAMES)
def test_every_script_has_a_drag_or_drop_on_a_drawn_handle_for_every_control(name: str) -> None:
    bs = parse(script_text(name))
    assert not isinstance(bs, str)
    for c in bs.controls:
        assert f'data-synapse-handle="{c.id}"' in bs.drawing, c.id
    assert "setPointerCapture" in bs.script and "pointermove" in bs.script


@pytest.mark.parametrize("name", NAMES)
def test_every_script_keeps_to_the_size_limits_and_the_writing_rules(name: str) -> None:
    raw = script_text(name)
    bs = parse(raw)
    assert not isinstance(bs, str)
    assert len(bs.script) <= 12000 and len(bs.drawing) <= 12000 and len(raw) <= 20000
    assert "—" not in raw and "–" not in raw
    assert "lab" not in " ".join([bs.title, bs.try_this, *bs.steps]).lower().split()


def test_one_script_uses_a_drop_so_a_drop_is_exercised() -> None:
    bs = parse(script_text("springs_series_planet"))
    assert not isinstance(bs, str)
    assert 'data-synapse-target="hanger"' in bs.drawing


def test_the_fixture_folder_holds_nothing_else() -> None:
    assert {p.suffix for p in Path(FIXTURES).iterdir()} == {".txt"}
