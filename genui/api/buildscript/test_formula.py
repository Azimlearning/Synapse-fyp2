"""FORMULAS: the grammar, the Python evaluator, the JavaScript emitter (run for real in Node and compared), and the unit check."""

from __future__ import annotations

import json
import math
import random
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

import pytest

from api.buildscript import formula as fm

CASES = json.loads((Path(__file__).parent / "formula_cases.json").read_text(encoding="utf-8"))
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="Node is not installed")


def py(expr: str, env: dict[str, float]) -> float:
    return fm.evaluate(fm.parse(expr), env)


@pytest.mark.parametrize("case", CASES, ids=lambda c: f"{c['expr']} {c['env']}")
def test_the_python_evaluator(case: dict) -> None:
    if case["expected"] == "error":
        with pytest.raises(fm.FormulaError):
            py(case["expr"], case["env"])
    elif case["expected"] is None:
        assert math.isfinite(py(case["expr"], case["env"]))
    else:
        assert py(case["expr"], case["env"]) == pytest.approx(case["expected"], rel=1e-12, abs=1e-12)


REFUSED = [
    ("", "empty"),
    ("2 x", "unexpected"),
    ("x +", "ends too soon"),
    ("1 +* 2", "unexpected"),
    ("((1)", "ends too soon"),
    ("x = 2", "not allowed"),
    ("1 < 2", "not allowed"),
    ("x.y", "not allowed"),
    ("a ? b : c", "not allowed"),
    ("x;y", "not allowed"),
    ("if(x)", "conditionals"),
    ("eval(x)", "eval"),
    ("random()", "randomness"),
    ("time", "time"),
    ("foo(1)", "not an allowed function"),
    ("sqrt()", "unexpected"),
    ("sqrt(1, 2)", "1 argument"),
    ("min(1)", "at least 2"),
    ("sqrt", "is a function"),
    ("x ** 2", "unexpected"),
    ("'a'", "not allowed"),
    ("a" * 400, "at most"),
    ("(" * 60 + "1" + ")" * 60, "too deeply"),
]


@pytest.mark.parametrize(("expr", "fragment"), REFUSED, ids=[r[0][:20] or "empty" for r in REFUSED])
def test_what_is_not_in_the_grammar_is_refused_with_a_reason(expr: str, fragment: str) -> None:
    with pytest.raises(fm.FormulaError) as e:
        fm.parse(expr)
    assert fragment in str(e.value)


def test_names_and_free_names() -> None:
    tree = fm.parse("g_earth * m + sqrt(x) / pi")
    assert fm.names(tree) == {"g_earth", "m", "x", "pi"}
    assert fm.free_names(tree) == {"m", "x"}


def test_a_name_without_a_value_is_an_error() -> None:
    with pytest.raises(fm.FormulaError, match="no value"):
        py("x + 1", {})


def test_constants_are_the_textbook_values() -> None:
    from api.pipeline import constants

    g = constants.find(None, None, ident="g")
    assert g is not None and fm.CONSTANTS["g_earth"][0] in g.accepted


# ── Node: the emitted JavaScript gives the same numbers, and no value where Python has none ──────────────────────────────────
def _run_node(samples: list[tuple[str, dict[str, float]]]) -> list[float | None]:
    body = ",\n".join(
        f"(function(){{var V={json.dumps(env)};return {fm.to_js(fm.parse(expr))};}})()" for expr, env in samples
    )
    script = f"{fm.JS_HELPERS}\nvar out=[\n{body}\n].map(function(x){{return isFinite(x)?x:null}});\nconsole.log(JSON.stringify(out));"
    out = subprocess.run([NODE, "-"], input=script, capture_output=True, text=True, timeout=60, check=False)  # type: ignore[list-item]
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _same(expr: str, env: dict[str, float], js: float | None) -> None:
    try:
        want: float | None = py(expr, env)
    except fm.FormulaError:
        want = None
    if want is None:
        assert js is None, f"{expr} {env}: Python has no value, JavaScript gave {js}"
    else:
        assert js is not None, f"{expr} {env}: JavaScript has no value, Python gave {want}"
        assert js == pytest.approx(want, rel=1e-9, abs=1e-12), f"{expr} {env}"


@needs_node
def test_every_case_agrees_in_python_and_node() -> None:
    got = _run_node([(c["expr"], c["env"]) for c in CASES])
    for c, js in zip(CASES, got, strict=True):
        _same(c["expr"], c["env"], js)
        if c["expected"] == "error":
            assert js is None


@needs_node
def test_random_inputs_agree_in_python_and_node() -> None:
    exprs = [
        "x * y + z",
        "1 / (1 / x + 1 / y)",
        "sqrt(x * y)",
        "x ^ 2 / (y + 3)",
        "2 * pi * sqrt(abs(x) / (abs(y) + 0.5))",
        "sqrt(2 * g_earth * x * (1 - cos(rad(y))))",
        "ln(x) + log10(abs(y) + 1)",
        "exp(x / 40) - min(y, z)",
        "atan(x) * deg(asin(y / 100))",
        "max(x, y, z) ^ 0.5",
        "x / (y - z)",
    ]
    rng = random.Random(20261117)
    samples = [(e, {"x": rng.uniform(-60, 60), "y": rng.uniform(-60, 60), "z": rng.uniform(-60, 60)}) for e in exprs for _ in range(150)]
    got = _run_node(samples)
    for (expr, env), js in zip(samples, got, strict=True):
        _same(expr, env, js)


# ── units ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def u(text: str) -> fm.Unit:
    got = fm.parse_unit(text)
    assert got is not None, text
    return got


def test_units_parse_by_dimension_and_scale() -> None:
    assert u("N/m").dims == (Fraction(0), Fraction(1), Fraction(-2), 0, 0, 0, 0)
    assert u("m/s^2") == u("m/s2") == u("N/kg")
    assert u("cm3").scale == pytest.approx(1e-6) and u("L").scale == pytest.approx(1e-3) and u("dm3").scale == pytest.approx(1e-3)
    assert u("L").dims == u("dm3").dims == u("m3").dims
    assert u("J") == u("N m") and u("Pa") == u("N/m^2") and u("W") == u("J/s")
    assert u("") == fm.ONE and u("deg") == fm.ONE and u("mol/dm3").dims[5] == 1
    assert fm.parse_unit("flurb") is None and fm.parse_unit("m/flurb") is None


def check(expr: str, units: dict[str, str], declared: str | None = None) -> None:
    fm.check_units(fm.parse(expr), {k: fm.parse_unit(v) for k, v in units.items()}, declared)


def test_a_consistent_formula_passes() -> None:
    check("m * g", {"m": "kg", "g": "N/kg"}, "N")
    check("1 / (1 / k1 + 1 / k2)", {"k1": "N/m", "k2": "N/m"}, "N/m")
    check("w / k", {"w": "N", "k": "N/m"}, "m")
    check("sqrt(l / g)", {"l": "m", "g": "m/s^2"}, "s")
    check("2 * pi * sqrt(l / g)", {"l": "m", "g": "N/kg"}, "s")
    check("sqrt(2 * g * l * (1 - cos(rad(a))))", {"g": "N/kg", "l": "m", "a": "deg"}, "m/s")


def test_adding_unlike_quantities_is_refused() -> None:
    with pytest.raises(fm.FormulaError, match="joins"):
        check("l + t", {"l": "m", "t": "s"})
    with pytest.raises(fm.FormulaError, match="different units"):
        check("min(l, t)", {"l": "m", "t": "s"})


def test_a_declared_unit_that_does_not_match_is_refused() -> None:
    with pytest.raises(fm.FormulaError, match="declared"):
        check("m * g", {"m": "kg", "g": "N/kg"}, "m")
    with pytest.raises(fm.FormulaError, match="declared"):
        check("w / k", {"w": "N", "k": "N/m"}, "N")


def test_trig_and_exp_need_pure_numbers() -> None:
    with pytest.raises(fm.FormulaError, match="pure number"):
        check("sin(l)", {"l": "m"})
    with pytest.raises(fm.FormulaError, match="pure number"):
        check("exp(t)", {"t": "s"})
    check("sin(rad(a))", {"a": "deg"})


def test_an_exponent_on_a_quantity_must_be_a_plain_number() -> None:
    with pytest.raises(fm.FormulaError, match="plain number"):
        check("l ^ t", {"l": "m", "t": "s"})
    check("l ^ 2", {"l": "m"}, "m^2")
    check("x ^ y", {"x": "", "y": "s"})


def test_bare_constants_stand_down_the_check_instead_of_refusing_a_right_formula() -> None:
    check("mass_g / 1000", {"mass_g": "g"}, "kg")  # a conversion: scale is not checked
    check("m * 9.81", {"m": "kg"}, "N")  # 9.81 may carry a unit: the unit is unknown, so nothing is claimed
    check("t - 273", {"t": "K"}, "K")  # a bare number joined to a quantity takes its unit
    check("max(0, a)", {"a": "m/s^2"}, "m/s^2")
    check("v - 25 / 2", {"v": "cm3"})


def test_scale_is_not_checked_but_dimension_is() -> None:
    check("a + b", {"a": "cm", "b": "m"})
    with pytest.raises(fm.FormulaError):
        check("a + b", {"a": "cm", "b": "s"})


def test_unknown_units_switch_the_check_off() -> None:
    check("a + b", {"a": "flurb", "b": "s"})
    check("a * b", {"a": "flurb", "b": "s"}, "m")
