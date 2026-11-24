"""The Build Script parser and the unit splitter."""

from __future__ import annotations

import pytest

from api.buildscript.conftest import PAIRS, script_text
from api.buildscript.parse import parse, parse_control, parse_formula, parse_part, parse_readout, units

NAMES = list(PAIRS)
SPRINGS = script_text("springs_series_planet")


@pytest.mark.parametrize("name", NAMES)
def test_every_fixture_parses(name: str) -> None:
    bs = parse(script_text(name))
    assert not isinstance(bs, str), bs
    assert bs.title and bs.controls and bs.readouts and bs.drawing and bs.script
    assert bs.parts == [] and bs.base is None


def test_the_springs_script_parses_into_its_parts() -> None:
    bs = parse(SPRINGS)
    assert not isinstance(bs, str)
    assert [c.id for c in bs.controls] == ["mass_g", "g_planet", "k1", "k2"]
    assert [f.name for f in bs.formulas][:3] == ["mass", "weight", "k_total"]
    assert bs.formulas[0].unit == "kg" and bs.formulas[0].expr == "mass_g / 1000"
    assert [(r.id, r.source, r.decimals) for r in bs.readouts] == [("r_w", "weight", 2), ("r_k", "k_total", 1), ("r_x", "x_cm", 1)]
    assert bs.predict is not None and bs.predict[1] == ["More", "Less", "The same"] and bs.predict[2].startswith("drop a mass")
    assert len(bs.steps) == 3 and len(bs.hints) == 2 and len(bs.explain) == 2 and len(bs.twists) == 2


def test_parts_may_be_listed_and_json_arguments_are_read() -> None:
    raw = SPRINGS.replace("@@PARTS\nnone", '@@PARTS\ng = planetGravity {"planet": "$p"}\nw = weight {"mass": 1.5, "gravity": "$g"}')
    bs = parse(raw)
    assert not isinstance(bs, str)
    assert bs.parts[0].component == "planetGravity" and bs.parts[0].args == {"planet": "$p"}
    assert bs.parts[1].args == {"mass": 1.5, "gravity": "$g"}


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        (lambda s: s.replace("@@END\n", ""), "cut off"),
        (lambda s: s.replace("@@HINTS", "@@HINT"), "not a section"),
        (lambda s: s.replace("@@KICKER\nPhysics, introductory\n", ""), "missing these sections: @@KICKER"),
        (lambda s: s.replace("@@TITLE", "@@TITLE\nX\n@@TITLE", 1), "appears twice"),
        (lambda s: s.replace("@@CONTROLS", "@@STYLE\n#bench-art{}\n@@CONTROLS", 1), "out of order"),
        (lambda s: s.replace('@@PARTS\nnone', '@@PARTS\nw = weight {"mass": }'), "not valid JSON"),
        (lambda s: s.replace('@@PARTS\nnone', '@@PARTS\nweight'), "not 'name = component"),
        (lambda s: s.replace("mass_g | Mass (g) | 0 | 500 | 50 | 100 | g", "mass_g | Mass (g) | 0 | 500"), "is not 'id | label"),
        (lambda s: s.replace("| 0 | 500 | 50 | 100 |", "| 0 | five | 50 | 100 |"), "not a number"),
        (lambda s: s.replace("| 0 | 500 | 50 | 100 |", "| 0 | 500 | 50 | 900 |"), "start inside the range"),
        (lambda s: s.replace("mass = mass_g / 1000 [kg]", "mass is mass_g / 1000"), "not 'name = expression"),
        (lambda s: s.replace("r_w | Weight (N) | weight | 2", "r_w | Weight (N) | weight"), "is not 'id | label"),
        (lambda s: s.replace("weight | 2", "weight | many"), "whole number"),
        (lambda s: s.replace("r_k | Combined stiffness (N/m) | k_total | 1", "r_k | Combined | not a name! | 1"), "source"),
        (lambda s: s.replace("r_k |", "r_w |"), "its own name"),
        (lambda s: s.replace("@@TITLE\nTwo springs in series on another planet", "@@TITLE\n"), "TITLE is empty"),
    ],
    ids=["cut-off", "unknown-section", "missing-section", "duplicate", "out-of-order", "bad-json", "bad-part", "short-control", "nan-control",
         "start-outside", "bad-formula", "short-readout", "bad-decimals", "bad-source", "duplicate-name", "empty-title"],
)  # fmt: skip
def test_a_malformed_reply_is_refused_with_a_reason_for_the_retry(change, fragment: str) -> None:  # noqa: ANN001
    reason = parse(change(SPRINGS))
    assert isinstance(reason, str) and fragment in reason, reason


def test_line_parsers_return_a_reason_not_an_exception() -> None:
    assert isinstance(parse_part("x"), str) and isinstance(parse_control("a | b"), str)
    assert isinstance(parse_formula("nope"), str) and isinstance(parse_readout("a | b"), str)
    f = parse_formula("x = a * (b + 2) [m/s^2]")
    assert not isinstance(f, str) and f.expr == "a * (b + 2)" and f.unit == "m/s^2"
    f = parse_formula("x = a * b")
    assert not isinstance(f, str) and f.unit is None


def test_crlf_replies_parse_the_same() -> None:
    a, b = parse(SPRINGS), parse(SPRINGS.replace("\n", "\r\n"))
    assert not isinstance(a, str) and not isinstance(b, str) and a == b


# ── the unit splitter ───────────────────────────────────────────────────────────────────────────────────────────────────────
def test_units_yield_text_sections_whole_and_line_sections_line_by_line() -> None:
    got = list(units(SPRINGS))
    sections = [u.section for u in got]
    assert sections[:3] == ["BASE", "TITLE", "KICKER"] and sections[-1] == "END"
    assert [u.text for u in got if u.section == "CONTROLS"][0].startswith("mass_g |")
    assert [u.index for u in got if u.section == "CONTROLS"] == [0, 1, 2, 3]
    assert len([u for u in got if u.section == "FORMULAS"]) == 7


def test_a_stream_never_yields_a_half_unit() -> None:
    """For every prefix of a reply, the units yielded are a prefix of the units of the whole reply: what has arrived is complete, and never changes later."""
    full = list(units(SPRINGS))
    for cut in list(range(0, len(SPRINGS), 61)) + [len(SPRINGS) - 1, len(SPRINGS)]:
        part = list(units(SPRINGS[:cut]))
        assert part == full[: len(part)], f"cut at {cut}"


def test_a_line_is_not_yielded_until_its_newline_has_arrived() -> None:
    head = "@@TITLE\nT\n@@CONTROLS\nmass_g | Mass (g) | 0 | 500 | 50 | 100 | g"
    assert [u.section for u in units(head)] == ["TITLE"]
    assert [u.section for u in units(head + "\n")] == ["TITLE", "CONTROLS"]


def test_units_stop_at_the_end_marker() -> None:
    got = list(units(SPRINGS + "@@EXTRA\nnot read\n"))
    assert got[-1].section == "END"
