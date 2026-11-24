"""Expected behaviour as test specs: each relation passes a conforming sweep and fails a violating one."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from api.blueprint.behaviour import BehaviourSpec, Verdict, compile_behaviours, holds
from api.schema.generated import Blueprint

FIXTURES = Path(__file__).parent / "fixtures"
XS = [0.0, 1.0, 2.0, 3.0, 4.0]


def spec(
    kind: str,
    *,
    variable: str = "x",
    low: float | None = None,
    high: float | None = None,
    at: float | None = None,
    value: float | None = None,
) -> BehaviourSpec:
    return BehaviourSpec(kind, "y", variable, low, high, at, value, "t")


def sweep(ys: list[float]) -> list[tuple[float, float]]:
    return list(zip(XS, ys, strict=True))


def test_rises_with() -> None:
    s = spec("rises-with")
    assert holds(s, sweep([1, 2, 3, 4, 5])).ok
    assert not holds(s, sweep([5, 4, 3, 2, 1])).ok
    assert not holds(s, sweep([1, 3, 2, 4, 5])).ok, "a real dip is not a rise"
    assert not holds(s, sweep([3, 3, 3, 3, 3])).ok, "a flat line is not rising"
    assert holds(s, sweep([1, 2, 3, 3.0, 5])).ok, "a plateau is allowed"


def test_falls_with() -> None:
    s = spec("falls-with")
    assert holds(s, sweep([5, 4, 3, 2, 1])).ok
    assert not holds(s, sweep([1, 2, 3, 4, 5])).ok
    assert not holds(s, sweep([3, 3, 3, 3, 3])).ok


def test_independent_of() -> None:
    s = spec("independent-of")
    assert holds(s, sweep([2.0, 2.0, 2.01, 2.0, 2.0])).ok
    assert not holds(s, sweep([1, 2, 3, 4, 5])).ok
    assert holds(s, sweep([2.0] * 5)).ok
    assert not holds(spec("rises-with"), sweep([2.0] * 5)).ok, "a constant series is independent, not rising"


def test_stays_within() -> None:
    s = spec("stays-within", low=0, high=14, variable="")
    assert holds(s, sweep([0, 3, 7, 12, 14])).ok
    over = holds(s, sweep([0, 3, 7, 12, 14.5]))
    assert not over.ok and "14.5" in over.reason
    assert not holds(s, sweep([-0.5, 3, 7, 12, 14])).ok
    assert not holds(spec("stays-within", variable=""), sweep([1, 2, 3, 4, 5])).ok, "no bounds is refused"


def test_equals_at() -> None:
    s = spec("equals-at", at=2.0, value=3.0)
    assert holds(s, sweep([1, 2, 3, 4, 5])).ok
    assert holds(s, sweep([1, 2.5, 3.02, 4, 5])).ok, "within the tolerance"
    assert not holds(s, sweep([1, 2, 4, 5, 6])).ok
    assert not holds(spec("equals-at", at=9.0, value=3.0), sweep([1, 2, 3, 4, 5])).ok, "the sweep never reaches 9"
    assert holds(spec("equals-at", at=0.5, value=1.5), sweep([1, 2, 3, 4, 5])).ok, "interpolates between points"
    assert holds(spec("equals-at", at=1.0, value=0.0), sweep([1, 0.005, 3, 4, 5])).ok


def test_degenerate_sweeps_are_refused() -> None:
    assert not holds(spec("rises-with"), [(0.0, 1.0)]).ok
    assert not holds(spec("rises-with"), sweep([1, 2, float("nan"), 4, 5])).ok
    assert not holds(spec("rises-with"), sweep([1, 2, float("inf"), 4, 5])).ok
    assert holds(spec("rises-with"), [(4, 5), (0, 1), (2, 3)]).ok, "order does not matter"
    assert holds(spec("nonsense"), sweep([1, 2, 3, 4, 5])) == Verdict(False, "unknown behaviour 'nonsense'")


def test_fixture_compiles_and_its_own_expectations_hold() -> None:
    bp = Blueprint.model_validate(json.loads((FIXTURES / "good_pendulum_angle.json").read_text(encoding="utf-8")))
    specs = compile_behaviours(bp)
    assert [s.kind for s in specs] == ["rises-with", "independent-of", "equals-at"]
    length = [0.2, 0.5, 1.0, 1.5, 2.0]
    period = [2 * math.pi * math.sqrt(x / 9.81) for x in length]
    assert holds(specs[0], list(zip(length, period, strict=True))).ok
    assert holds(specs[2], list(zip(length, period, strict=True))).ok, "T at 1 m is about 2.006 s"
    angle = [2.0, 5.0, 10.0, 15.0, 20.0]
    t_angle = [2.006 * (1 + math.radians(a) ** 2 / 16) for a in angle]  # the first term of the large-angle correction: under 1 percent at 20 degrees
    assert holds(specs[1], list(zip(angle, t_angle, strict=True))).ok


@pytest.mark.parametrize("kind", ["rises-with", "falls-with", "independent-of", "stays-within", "equals-at"])
def test_every_kind_in_the_wire_type_is_handled(kind: str) -> None:
    v = holds(spec(kind, low=0, high=9, at=1.0, value=2.0), sweep([1, 2, 3, 4, 5]))
    assert "unknown behaviour" not in v.reason
