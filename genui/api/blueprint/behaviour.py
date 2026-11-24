"""Expected behaviour as data a test can run (blueprint.md section 5).

`compile_behaviours` turns each `BlueprintBehaviour` into a `BehaviourSpec`: which variable to sweep, which measured value to read, and the relation to hold.
`holds` judges one sweep against one spec. It is pure, so the relations are tested here without a browser; the sweep itself (drive the control, read the readout) is
run in the real browser by the verification harness. Nothing here trusts the Environment: it compares numbers the page produced with a relation the plan stated.

Tolerances are relative to the size of the measured values, so a spec does not depend on the unit. They are deliberately loose enough for a drawing's rounding and
tight enough that a flat line is not "rising" and a rising one is not "independent".
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from api.schema.generated import Blueprint

NOISE = 0.005
"""A step may fall (for 'rises-with') by this share of the largest measured value before it counts as a fall: rounding, not a trend."""
FLAT = 0.02
"""'independent-of' allows the measured value to move by this share of its largest size (a small-angle pendulum is not perfectly independent)."""
POINT = 0.02
"""'equals-at' allows this share of the stated value, or 0.01 when the stated value is 0."""
RISE = 0.01
"""'rises-with' and 'falls-with' need the whole sweep to move by at least this share of the largest measured value."""


@dataclass(frozen=True)
class BehaviourSpec:
    kind: str
    measured: str
    variable: str
    low: float | None
    high: float | None
    at: float | None
    value: float | None
    text: str


@dataclass(frozen=True)
class Verdict:
    ok: bool
    reason: str = ""


def compile_behaviours(bp: Blueprint) -> list[BehaviourSpec]:
    """One spec per expected behaviour, in the Blueprint's order. The Blueprint is assumed to have passed `checks.check`."""
    return [BehaviourSpec(b.kind, b.measured, b.variable, b.low, b.high, b.at, b.value, b.text) for b in bp.expectedBehaviour]


def holds(spec: BehaviourSpec, samples: Sequence[tuple[float, float]]) -> Verdict:
    """Does a sweep satisfy the spec? `samples` is (variable value, measured value) pairs; order does not matter."""
    pts = sorted((float(x), float(y)) for x, y in samples)
    if len(pts) < 2:
        return Verdict(False, "a sweep needs at least two points")
    if any(not (math.isfinite(x) and math.isfinite(y)) for x, y in pts):
        return Verdict(False, "the sweep has a value that is not finite")
    ys = [y for _, y in pts]
    scale = max(max(abs(y) for y in ys), 1e-12)

    if spec.kind == "stays-within":
        lo, hi = spec.low, spec.high
        if lo is None or hi is None:
            return Verdict(False, "'stays-within' needs low and high")
        eps = 1e-9 * max(scale, 1.0)
        bad = [y for y in ys if y < lo - eps or y > hi + eps]
        return Verdict(False, f"{spec.measured} reached {bad[0]:g}, outside {lo:g} to {hi:g}") if bad else Verdict(True)

    if spec.kind in ("rises-with", "falls-with"):
        sign = 1.0 if spec.kind == "rises-with" else -1.0
        steps = [sign * (b - a) for a, b in zip(ys, ys[1:], strict=False)]
        if any(s < -NOISE * scale for s in steps):
            return Verdict(False, f"{spec.measured} moves the wrong way as {spec.variable} grows")
        if sign * (ys[-1] - ys[0]) < RISE * scale:
            return Verdict(False, f"{spec.measured} does not {'rise' if sign > 0 else 'fall'} enough across the sweep of {spec.variable}")
        return Verdict(True)

    if spec.kind == "independent-of":
        spread = max(ys) - min(ys)
        return Verdict(True) if spread <= FLAT * scale else Verdict(False, f"{spec.measured} moves by {spread:g} across the sweep of {spec.variable}")

    if spec.kind == "equals-at":
        if spec.at is None or spec.value is None:
            return Verdict(False, "'equals-at' needs 'at' and 'value'")
        if not pts[0][0] <= spec.at <= pts[-1][0]:
            return Verdict(False, f"the sweep does not reach {spec.variable} = {spec.at:g}")
        got = _interpolate(pts, spec.at)
        tol = POINT * abs(spec.value) if spec.value != 0 else 0.01
        return Verdict(True) if abs(got - spec.value) <= tol else Verdict(False, f"{spec.measured} is {got:g} at {spec.variable} = {spec.at:g}, expected {spec.value:g}")

    return Verdict(False, f"unknown behaviour '{spec.kind}'")


def _interpolate(pts: list[tuple[float, float]], x: float) -> float:
    for (x0, y0), (x1, y1) in zip(pts, pts[1:], strict=False):
        if x0 <= x <= x1:
            return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1]
