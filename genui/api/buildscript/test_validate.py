"""The Build Script validator: every fixture passes, every rule refuses its own planted defect with its id and a reason, and a reply is checked unit by unit."""

from __future__ import annotations

import pytest

from api import kitmanifest
from api.blueprint.checks import Finding
from api.buildscript.conftest import PAIRS, script_text
from api.buildscript.model import Unit
from api.buildscript.parse import units
from api.buildscript.validate import Validator, validate

NAMES = list(PAIRS)
SPRINGS = script_text("springs_series_planet")
STORED = frozenset({"hookes_spring"})


def rules(findings: list[Finding]) -> set[str]:
    return {f.rule for f in findings}


@pytest.mark.parametrize("name", NAMES)
def test_every_fixture_passes(name: str, manifest: kitmanifest.Manifest) -> None:
    assert validate(script_text(name), manifest, STORED, early_stop=False) == []


def test_a_valid_stream_never_fails_on_a_prefix(manifest: kitmanifest.Manifest) -> None:
    """Units arrive complete and every reference points backwards, so no prefix of a good reply produces a finding."""
    for name in NAMES:
        raw = script_text(name)
        for cut in range(0, len(raw), 97):
            v = Validator(manifest, STORED)
            found = [f for u in units(raw[:cut]) for f in v.feed(u)]
            assert found == [], (name, cut, found[:1])


# (rule, change to the springs fixture). Each plants one defect.
REPLY_CASES = {
    "BS-000 cut off": ("BS-000", lambda s: s.replace("@@END\n", "")),
    "BS-001 long title": ("BS-001", lambda s: s.replace("Two springs in series on another planet", "T" * 70)),
    "BS-001 long dash": ("BS-001", lambda s: s.replace("- Both springs carry", "- Both springs — carry")),
    "BS-001 markup": ("BS-001", lambda s: s.replace("Drag the mass tile", "Drag the <b>mass</b> tile")),
    "BS-001 markdown": ("BS-001", lambda s: s.replace("Drag the mass tile", "Drag the `mass` tile")),
    "BS-001 two steps": ("BS-001", lambda s: s.replace("- Drag the ring of the lower spring to make it stiffer and watch the total stretch fall.\n", "")),
    "BS-001 one hint": ("BS-001", lambda s: s.replace("- A weaker planet pulls the same mass with less force.\n", "")),
    "BS-001 one paragraph": ("BS-001", lambda s: s.replace("\n\nA planet with weaker gravity", "\nA planet with weaker gravity")),
    "BS-001 predict without check": ("BS-001", lambda s: s.replace("Check: drop a mass", "Just drop a mass")),
    "BS-001 unknown base": ("BS-001", lambda s: s.replace("@@BASE\nnone", "@@BASE\nnot_stored")),
    "BS-003 constant not the textbook's": ("BS-003", lambda s: s.replace("g_planet | Gravity here (N/kg) | 1 | 25 | 0.5 | 3.5 | N/kg", "gravity | Gravity here (N/kg) | 1 | 25 | 0.5 | 10 | N/kg").replace("g_planet", "gravity")),
    "BS-003 reserved name": ("BS-003", lambda s: s.replace("k2 | Stiffness of spring 2", "sqrt | Stiffness of spring 2").replace("k2", "sqrt")),
    "BS-004 grammar": ("BS-004", lambda s: s.replace("x = x1 + x2 [m]", "x = x1 +* x2 [m]")),
    "BS-004 unknown name": ("BS-004", lambda s: s.replace("x1 = weight / k1 [m]", "x1 = weight / k9 [m]")),
    "BS-004 forward reference": ("BS-004", lambda s: s.replace("mass = mass_g / 1000 [kg]\nweight = mass * g_planet [N]", "weight = mass * g_planet [N]\nmass = mass_g / 1000 [kg]")),
    "BS-004 unit mismatch": ("BS-004", lambda s: s.replace("x = x1 + x2 [m]", "x = x1 + weight [m]")),
    "BS-004 declared unit wrong": ("BS-004", lambda s: s.replace("x1 = weight / k1 [m]", "x1 = weight / k1 [N]")),
    "BS-004 disallowed function": ("BS-004", lambda s: s.replace("x = x1 + x2 [m]", "x = eval(x1) [m]")),
    "BS-005 unknown source": ("BS-005", lambda s: s.replace("r_x | Total stretch (cm) | x_cm | 1", "r_x | Total stretch (cm) | x_cn | 1")),
    "BS-005 label without unit": ("BS-005", lambda s: s.replace("r_w | Weight (N) | weight | 2", "r_w | Weight | weight | 2")),
    "BS-006 selector outside the drawing": ("BS-006", lambda s: s.replace("#bench-art .rail{", "body{background:red}\n#bench-art .rail{")),
    "BS-006 transition outside reduced-motion": ("BS-006", lambda s: s.replace("#bench-art .lbl{", "#bench-art .spring{transition:all 1s}\n#bench-art .lbl{")),
    "BS-006 import": ("BS-006", lambda s: s.replace("#bench-art .lbl{", "@import 'x';\n#bench-art .lbl{")),
    "BS-006 two svgs": ("BS-006", lambda s: s.replace("</svg>", "</svg><svg id=\"bench-art\"></svg>")),
    "BS-006 no aria-label": ("BS-006", lambda s: s.replace(' aria-label="Two springs hanging in a row from a bar, with a mass hanger below"', "")),
    "BS-006 absolute url": ("BS-006", lambda s: s.replace('<svg id="bench-art"', '<svg xmlns="http://www.w3.org/2000/svg" id="bench-art"')),
    "BS-006 image": ("BS-006", lambda s: s.replace("</svg>", '<image href="a.png"/></svg>', 1)),
    "BS-007 fetch": ("BS-007", lambda s: s.replace('var svg = document.getElementById("bench-art");', 'var svg = document.getElementById("bench-art"); fetch("/x");', 1)),
    "BS-007 unknown host call": ("BS-007", lambda s: s.replace('host.on("mass", draw);', 'host.on("mass", draw); host.explode();')),
    "BS-007 writes a readout": ("BS-007", lambda s: s.replace('host.on("mass", draw);', 'host.on("mass", draw); document.getElementById("r_w").textContent = "1";')),
    "BS-007 host.readout without script source": ("BS-007", lambda s: s.replace('host.on("mass", draw);', 'host.on("mass", draw); host.readout("r_w", 1);')),
    "BS-007 script tag": ("BS-007", lambda s: s.replace('host.on("mass", draw);', 'host.on("mass", draw); </script>')),
    "BS-007 eval": ("BS-007", lambda s: s.replace('host.on("mass", draw);', 'host.on("mass", draw); eval("1");')),
    "BS-008 control without a handle": ("BS-008", lambda s: s.replace(' data-synapse-handle="k1"', "")),
    "BS-008 control changes nothing": ("BS-008", lambda s: s.replace("x2 = weight / k2 [m]", "x2 = weight / k1 [m]").replace("1 / (1 / k1 + 1 / k2)", "1 / (1 / k1 + 1 / k1)")),
    "BS-008 script readout never fed": ("BS-008", lambda s: s.replace("r_x | Total stretch (cm) | x_cm | 1", "r_x | Total stretch (cm) | script | 1")),
}  # fmt: skip


@pytest.mark.parametrize("label", list(REPLY_CASES))
def test_each_rule_refuses_its_defect(label: str, manifest: kitmanifest.Manifest) -> None:
    rule, change = REPLY_CASES[label]
    raw = change(SPRINGS)
    assert raw != SPRINGS, f"{label}: the change did not apply"
    findings = validate(raw, manifest, STORED, early_stop=False)
    assert rule in rules(findings), f"{label}: expected {rule}, got {sorted(rules(findings))} {findings[:2]}"
    own = [f for f in findings if f.rule == rule]
    assert all(f.reason and f.fix and f.path for f in own)


def test_every_rule_family_has_a_planted_defect() -> None:
    covered = {r for r, _ in REPLY_CASES.values()}
    assert covered >= {"BS-000", "BS-001", "BS-003", "BS-004", "BS-005", "BS-006", "BS-007", "BS-008"}


# BS-002 (parts) is checked unit by unit, since the fixtures list no parts.
def part(line: str, manifest: kitmanifest.Manifest, before: tuple[str, ...] = ()) -> list[Finding]:
    v = Validator(manifest, STORED)
    for ln in before:
        assert v.feed(Unit("CONTROLS", ln, 0)) == []
    return v.feed(Unit("PARTS", line, 0))


def test_a_good_part_line_passes_and_defines_its_name(manifest: kitmanifest.Manifest) -> None:
    v = Validator(manifest, STORED)
    assert v.feed(Unit("CONTROLS", "p | Planet | 1 | 8 | 1 | 3 | planet", 0)) == []
    assert v.feed(Unit("PARTS", 'g = planetGravity {"planet": "$p"}', 0)) == []
    assert v.feed(Unit("FORMULAS", "w = 2 * g [N/kg]", 0)) == []


@pytest.mark.parametrize(
    ("line", "fragment"),
    [
        ('x = teleporter {"a": 1}', "no part"),
        ("x = saved.p1 {}", "no saved parts"),
        ('x = weight {"mass": }', "not valid JSON"),
        ('x = weight {"mass": "$nothing", "gravity": 9.8}', "not defined before"),
        ('x = weight {"mass": 1, "gravity": 9.8, "bogus": 2}', "no argument 'bogus'"),
        ('x = weight {"mass": 1}', "needs the argument 'gravity'"),
        ('x = weight {"mass": -1, "gravity": 9.8}', "outside the domain"),
        ('sqrt = weight {"mass": 1, "gravity": 9.8}', "reserved"),
    ],
    ids=["unknown", "saved", "bad-json", "forward-ref", "unknown-arg", "missing-arg", "domain", "reserved"],
)
def test_each_part_defect_is_refused(line: str, fragment: str, manifest: kitmanifest.Manifest) -> None:
    got = part(line, manifest)
    assert got and all(f.rule == "BS-002" for f in got) and any(fragment in f.reason for f in got), got


def test_a_control_name_cannot_be_used_twice(manifest: kitmanifest.Manifest) -> None:
    """The whole-reply parse refuses a duplicate first; fed unit by unit, the validator refuses it on arrival."""
    v = Validator(manifest, STORED)
    assert v.feed(Unit("CONTROLS", "k1 | Stiffness (N/m) | 10 | 50 | 5 | 20 | N/m", 0)) == []
    got = v.feed(Unit("CONTROLS", "k1 | Other (N/m) | 10 | 50 | 5 | 20 | N/m", 1))
    assert got and got[0].rule == "BS-003" and "already used" in got[0].reason


def test_a_name_cannot_be_defined_twice(manifest: kitmanifest.Manifest) -> None:
    got = part('mass = weight {"mass": 1, "gravity": 9.8}', manifest, ("mass | Mass (kg) | 0 | 5 | 1 | 1 | kg",))
    assert got and "already used" in got[0].reason


# ── early stop and the shape of what comes back ─────────────────────────────────────────────────────────────────────────────
def test_early_stop_reports_only_the_first_failing_unit(manifest: kitmanifest.Manifest) -> None:
    raw = SPRINGS.replace("x1 = weight / k1 [m]", "x1 = weight / k9 [m]").replace("x2 = weight / k2 [m]", "x2 = weight / k8 [m]")
    stopped = validate(raw, manifest, STORED)
    full = validate(raw, manifest, STORED, early_stop=False)
    assert len(stopped) == 1 and stopped[0].path.startswith("@@FORMULAS")
    assert len(full) > len(stopped)


def test_a_reply_that_is_not_a_build_script_gives_one_finding_with_the_parse_reason(manifest: kitmanifest.Manifest) -> None:
    got = validate("hello", manifest)
    assert len(got) == 1 and got[0].rule == "BS-000" and "missing these sections" in got[0].reason


def test_findings_use_no_long_dashes(manifest: kitmanifest.Manifest) -> None:
    for label, (_, change) in REPLY_CASES.items():
        for f in validate(change(SPRINGS), manifest, STORED, early_stop=False):
            assert "—" not in str(f) and "–" not in str(f), label
