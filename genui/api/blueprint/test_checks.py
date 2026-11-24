"""The Blueprint checker (BP-001 to BP-010): good fixtures pass, and each rule refuses its own planted defect with its id and a reason."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from api import kitmanifest
from api.blueprint.checks import check
from api.kit import latest_version
from api.schema.generated import Blueprint

FIXTURES = Path(__file__).parent / "fixtures"
GOOD = sorted(FIXTURES.glob("good_*.json"))
STORED = frozenset({"hookes_spring"})
LONG_DASHES = ("—", "–")


@pytest.fixture(scope="module")
def manifest(kit_dist: Path) -> kitmanifest.Manifest:
    return kitmanifest.load(kit_dist, latest_version(kit_dist))


def raw(name: str = "good_hookes_mars_series.json") -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def run(data: dict, manifest: kitmanifest.Manifest) -> list:
    return check(Blueprint.model_validate(data), manifest, STORED)


def rules(findings: list) -> list[str]:
    return [f.rule for f in findings]


def mutated(fn, name: str = "good_hookes_mars_series.json") -> dict:
    data = copy.deepcopy(raw(name))
    fn(data)
    return data


@pytest.mark.parametrize("path", GOOD, ids=lambda p: p.stem)
def test_good_fixtures_pass(path: Path, manifest: kitmanifest.Manifest) -> None:
    assert run(json.loads(path.read_text(encoding="utf-8")), manifest) == []


def test_at_least_three_good_fixtures() -> None:
    assert len(GOOD) >= 3


# label: (rule, mutation). Each plants one defect in an otherwise good Blueprint.
CASES = {
    "BP-001 empty goal": ("BP-001", lambda d: d.update(goal=" ")),
    "BP-001 long concept": ("BP-001", lambda d: d.update(concept="x" * 300)),
    "BP-001 no science": ("BP-001", lambda d: d.update(science=[])),
    "BP-001 duplicate name": ("BP-001", lambda d: d["variables"][1].update(name="mass_g")),
    "BP-001 bad name": ("BP-001", lambda d: d["variables"][0].update(name="1 mass")),
    "BP-002 no measured": ("BP-002", lambda d: d["variables"][4].update(role="fixed")),
    "BP-002 no changed": ("BP-002", lambda d: [v.update(role="fixed") for v in d["variables"][:4]]),
    "BP-002 five changed": ("BP-002", lambda d: d["variables"].append({"name": "k3", "unit": "N/m", "min": 1, "max": 9, "role": "changed"})),
    "BP-003 changed variable not worked": ("BP-003", lambda d: d["interactions"].pop(2)),
    "BP-003 interaction on measured": ("BP-003", lambda d: d["interactions"][0].update(variable="x_cm")),
    "BP-003 unknown variable": ("BP-003", lambda d: d["interactions"][0].update(variable="ghost")),
    "BP-003 empty target": ("BP-003", lambda d: d["interactions"][0].update(target="")),
    "BP-004 no drag or drop": ("BP-004", lambda d: [i.update(gesture="rotate") for i in d["interactions"]]),
    "BP-005 slider object": ("BP-005", lambda d: d["interactions"][1].update(object="a slider")),
    "BP-005 button target": ("BP-005", lambda d: d["interactions"][0].update(target="the Add button")),
    "BP-006 odd unit": ("BP-006", lambda d: d["variables"][0].update(unit="<b>kg</b>")),
    "BP-006 min not below max": ("BP-006", lambda d: d["variables"][0].update(min=1, max=1)),
    "BP-006 model unit": ("BP-006", lambda d: d["variables"].append({"name": "load", "unit": "kg", "min": 0, "max": 5, "role": "fixed"})),
    "BP-006 model domain": ("BP-006", lambda d: d["variables"].append({"name": "load", "unit": "N", "min": -5, "max": 5, "role": "fixed"})),
    "BP-007 unknown kit part": ("BP-007", lambda d: d["assists"].append({"kind": "kit-part", "id": "teleporter"})),
    "BP-007 unknown stored": ("BP-007", lambda d: d["assists"].append({"kind": "stored-environment", "id": "nothing_here"})),
    "BP-007 saved part": ("BP-007", lambda d: d["assists"].append({"kind": "saved-part", "id": "p1"})),
    "BP-008 measured not measured": ("BP-008", lambda d: d["expectedBehaviour"][0].update(measured="mass_g")),
    "BP-008 swept not changed": ("BP-008", lambda d: d["expectedBehaviour"][0].update(variable="x_cm")),
    "BP-008 stays-within no bounds": ("BP-008", lambda d: d["expectedBehaviour"][2].update(low=None)),
    "BP-008 stays-within reversed": ("BP-008", lambda d: d["expectedBehaviour"][2].update(low=5, high=1)),
    "BP-008 empty text": ("BP-008", lambda d: d["expectedBehaviour"][0].update(text="")),
    "BP-009 one behaviour": ("BP-009", lambda d: d["expectedBehaviour"].__delitem__(slice(1, None))),
    "BP-009 two steps": ("BP-009", lambda d: d["steps"].pop()),
    "BP-009 one choice": ("BP-009", lambda d: d["predict"].update(choices=["Only"])),
    "BP-009 no question": ("BP-009", lambda d: d["predict"].update(question="")),
    "BP-010 narrow": ("BP-010", lambda d: d["scene"].update(widthShare=0.3)),
    "BP-010 short": ("BP-010", lambda d: d["scene"].update(heightShare=0.4)),
    "BP-010 no fills": ("BP-010", lambda d: d["scene"].update(fills=[])),
    "BP-010 no wide screen": ("BP-010", lambda d: d["scene"].update(wideScreen="")),
    "BP-010 share above one": ("BP-010", lambda d: d["scene"].update(widthShare=1.4)),
}


@pytest.mark.parametrize("label", list(CASES))
def test_each_rule_refuses_its_defect(label: str, manifest: kitmanifest.Manifest) -> None:
    rule, fn = CASES[label]
    findings = run(mutated(fn), manifest)
    assert rule in rules(findings), f"{label}: expected {rule}, got {rules(findings)}"
    own = [f for f in findings if f.rule == rule]
    assert all(f.reason and f.fix and f.path for f in own)


def test_every_rule_has_a_planted_defect() -> None:
    assert {r for r, _ in CASES.values()} == {f"BP-{n:03d}" for n in range(1, 11)}


def test_a_defect_does_not_raise_unrelated_rules(manifest: kitmanifest.Manifest) -> None:
    """These planted defects trip their own rule and no other."""
    for label in ("BP-003 changed variable not worked", "BP-004 no drag or drop", "BP-003 interaction on measured"):
        rule, fn = CASES[label]
        assert set(rules(run(mutated(fn), manifest))) == {rule}, label


def test_findings_are_in_rule_order_and_readable(manifest: kitmanifest.Manifest) -> None:
    data = mutated(lambda d: (d.update(goal=""), d["scene"].update(widthShare=0.2), d["interactions"].pop(0)))
    findings = run(data, manifest)
    assert rules(findings) == sorted(rules(findings))
    assert "BP-001" in str(findings[0]) and "goal" in str(findings[0])


def test_a_slider_only_plan_is_refused(manifest: kitmanifest.Manifest) -> None:
    def only_sliders(d: dict) -> None:
        for i in d["interactions"]:
            i["object"] = "a slider"

    assert "BP-005" in rules(run(mutated(only_sliders), manifest))


def test_no_long_dashes_in_any_finding_or_fixture(manifest: kitmanifest.Manifest) -> None:
    for label, (_, fn) in CASES.items():
        for f in run(mutated(fn), manifest):
            assert not any(d in str(f) for d in LONG_DASHES), label
    for p in FIXTURES.glob("*.json"):
        text = p.read_text(encoding="utf-8")
        assert not any(d in text for d in LONG_DASHES), p.name


def test_the_wire_model_refuses_what_the_checker_never_sees() -> None:
    """Shape errors (a wrong gesture, an extra field, a string for a number) stop at the strict model, before the checker."""
    with pytest.raises(ValidationError):
        Blueprint.model_validate(mutated(lambda d: d["interactions"][0].update(gesture="slide")))
    with pytest.raises(ValidationError):
        Blueprint.model_validate(mutated(lambda d: d.update(extra=1)))
    with pytest.raises(ValidationError):
        Blueprint.model_validate(mutated(lambda d: d["scene"].update(widthShare="0.7")))
