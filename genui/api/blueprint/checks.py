"""Deterministic checks on an Environment Blueprint (V5-D18, V5-D23). No model call, no I/O.

Spec: refdocs/v5-design/docs/blueprint.md section 3 and 7. Each finding carries a rule id, the path of the field at fault, the reason in plain words and the
fix, in the same shape as v4's plan findings, so one retry can quote the checker's own words back to the planner. v4's `PLAN-0xx` rules stay with the Compose lane;
the rules here are `BP-001` onward.

A Blueprint that passes is a plan worth writing from. It proves nothing about the Environment that will be built from it: the writer's output still faces every
check the Free lane has, and the browser checks the result.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from api.kitmanifest import Manifest
from api.schema.generated import Blueprint

MIN_WIDTH_SHARE = 0.55
MIN_HEIGHT_SHARE = 0.5
MAX_CHANGED = 4
"""The house frame carries at most this many controls (`free_house.MAX_CONTROLS`)."""
MAX_VARIABLES = 8
MAX_INTERACTIONS = 6
MAX_BEHAVIOURS = 8

_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,39}")
_UNIT = re.compile(r"[A-Za-z0-9µμ°%/^*.() \-]{0,20}")
_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_.]*")
_WIDGET = re.compile(r"\b(slider|button|dropdown|drop-down|checkbox|check box|text field|text box|input box|toggle|switch)\b", re.IGNORECASE)
_PHYSICAL = ("drag", "drop")
_TEXT_LIMITS = {"concept": 240, "goal": 240, "phenomenon": 480, "motion": 320}


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    reason: str
    fix: str

    def __str__(self) -> str:
        return f"{self.rule} at {self.path}: {self.reason} {self.fix}"


def check(blueprint: Blueprint, manifest: Manifest, stored_ids: frozenset[str] | set[str] = frozenset()) -> list[Finding]:
    """Every finding, in rule order. An empty list means the Blueprint passes."""
    out: list[Finding] = []

    def add(rule: str, path: str, reason: str, fix: str) -> None:
        out.append(Finding(rule, path, reason, fix))

    _bp001(blueprint, add)
    _bp002(blueprint, add)
    _bp003_005(blueprint, add)
    _bp006(blueprint, manifest, add)
    _bp007(blueprint, manifest, stored_ids, add)
    _bp008(blueprint, add)
    _bp009(blueprint, add)
    _bp010(blueprint, add)
    return sorted(out, key=lambda f: f.rule)


def _finite(x: float | None) -> bool:
    return x is not None and math.isfinite(x)


def _bp001(bp: Blueprint, add) -> None:
    """BP-001: the required fields are present and within their length limits."""
    for name, limit in _TEXT_LIMITS.items():
        text = getattr(bp, name).strip()
        if not text:
            add("BP-001", name, f"'{name}' is empty.", f"Write {name} in one or two plain sentences.")
        elif len(text) > limit:
            add("BP-001", name, f"'{name}' is {len(text)} characters, over {limit}.", f"Shorten {name} to {limit} characters or fewer.")
    if not [s for s in bp.science if s.strip()]:
        add("BP-001", "science", "'science' names no law or rule.", "Name a Kit model id, a formula, or describe the computation the model code will do.")
    if not bp.variables:
        add("BP-001", "variables", "There are no variables.", "List each quantity with its name, unit, range and role.")
    if len(bp.variables) > MAX_VARIABLES:
        add("BP-001", "variables", f"There are {len(bp.variables)} variables, over {MAX_VARIABLES}.", f"Keep the {MAX_VARIABLES} that matter.")
    if len(bp.interactions) > MAX_INTERACTIONS:
        add("BP-001", "interactions", f"There are {len(bp.interactions)} interactions, over {MAX_INTERACTIONS}.", f"Keep at most {MAX_INTERACTIONS}.")
    if len(bp.expectedBehaviour) > MAX_BEHAVIOURS:
        add("BP-001", "expectedBehaviour", f"There are {len(bp.expectedBehaviour)} expected behaviours, over {MAX_BEHAVIOURS}.", f"Keep at most {MAX_BEHAVIOURS}.")
    for i, s in enumerate(bp.steps):
        if not s.strip():
            add("BP-001", f"steps[{i}]", "A step is empty.", "Write each step as one sentence, or remove it.")
    seen: set[str] = set()
    for i, v in enumerate(bp.variables):
        where = f"variables[{i}]"
        if not _NAME.fullmatch(v.name):
            add("BP-001", f"{where}.name", f"'{v.name}' is not a usable name.", "Use letters, digits and underscores, starting with a letter, up to 40 characters.")
        elif v.name in seen:
            add("BP-001", f"{where}.name", f"The name '{v.name}' is used twice.", "Give every variable its own name.")
        seen.add(v.name)


def _bp002(bp: Blueprint, add) -> None:
    """BP-002: something the student changes, something measured, and no more controls than the house frame holds."""
    changed = [v for v in bp.variables if v.role == "changed"]
    measured = [v for v in bp.variables if v.role == "measured"]
    if not changed:
        add("BP-002", "variables", "No variable is changed by the student.", "Mark at least one variable with the role 'changed'.")
    if not measured:
        add("BP-002", "variables", "No variable is measured.", "Mark at least one variable with the role 'measured', the thing the student watches.")
    if len(changed) > MAX_CHANGED:
        add("BP-002", "variables", f"The student changes {len(changed)} variables, over {MAX_CHANGED}.", f"Let the student change at most {MAX_CHANGED}; mark the rest 'fixed'.")


def _bp003_005(bp: Blueprint, add) -> None:
    """BP-003: every changed variable is worked by hand on a drawn object. BP-004: at least one drag or drop. BP-005: never a slider or a button alone."""
    roles = {v.name: v.role for v in bp.variables}
    worked: set[str] = set()
    for i, it in enumerate(bp.interactions):
        where = f"interactions[{i}]"
        role = roles.get(it.variable)
        if role is None:
            add("BP-003", f"{where}.variable", f"'{it.variable}' is not a declared variable.", "Name a variable from the variables list.")
        elif role != "changed":
            add("BP-003", f"{where}.variable", f"'{it.variable}' is {role}, not changed by the student.", "An interaction belongs to a variable the student changes.")
        else:
            worked.add(it.variable)
        for field in ("object", "target", "response"):
            if not getattr(it, field).strip():
                add("BP-003", f"{where}.{field}", f"The interaction's {field} is empty.", f"Say what the {field} is, in plain words.")
        for field in ("object", "target"):
            m = _WIDGET.search(getattr(it, field))
            if m:
                add(
                    "BP-005",
                    f"{where}.{field}",
                    f"The {field} is '{getattr(it, field)}': a {m.group(1).lower()} is not a drawn object.",
                    "Name a thing the bench draws (a mass, a lever, a dropper, a lens) and a gesture on it. A slider exists only as the keyboard fallback.",
                )
    for v in bp.variables:
        if v.role == "changed" and v.name not in worked:
            add("BP-003", "interactions", f"The student changes '{v.name}' but no interaction works it by hand.", f"Add an interaction for '{v.name}': the drawn object they touch, the gesture, the target and the motion that answers.")
    if not any(it.gesture in _PHYSICAL for it in bp.interactions):
        add("BP-004", "interactions", "No interaction is a drag or a drop.", "Make at least one interaction a drag (along a path) or a drop (onto a target).")


def _bp006(bp: Blueprint, manifest: Manifest, add) -> None:
    """BP-006: units are plain and finite ranges are ordered; where a Kit model is named, its inputs keep to its unit and domain."""
    for i, v in enumerate(bp.variables):
        where = f"variables[{i}]"
        if not _UNIT.fullmatch(v.unit):
            add("BP-006", f"{where}.unit", f"The unit '{v.unit}' is not a plain unit.", "Write a short unit such as N, N/m, m/s^2, g or kg.")
        if not (_finite(v.min) and _finite(v.max)):
            add("BP-006", where, f"'{v.name}' has a range that is not finite.", "Give finite numbers for min and max.")
        elif not v.min < v.max:
            add("BP-006", where, f"'{v.name}' runs from {v.min:g} to {v.max:g}.", "Set min below max.")
    named = {t for s in bp.science for t in _TOKEN.findall(s)}
    for model in manifest.models.values():
        if model.model_id not in named and model.export_name not in named:
            continue
        for i, v in enumerate(bp.variables):
            q = model.inputs.get(v.name)
            if q is None:
                continue
            where = f"variables[{i}]"
            if v.unit.strip() != q.unit.strip():
                add("BP-006", f"{where}.unit", f"The Kit model {model.export_name} takes '{v.name}' in {q.unit}, and the Blueprint gives {v.unit or 'no unit'}.", f"Use {q.unit}.")
            if not (_finite(v.min) and _finite(v.max)):
                continue
            low_bad = v.min < q.min or (q.exclusive and v.min <= q.min)
            high_bad = q.max is not None and (v.max > q.max or (q.max_exclusive and v.max >= q.max))
            if low_bad or high_bad:
                top = f" up to {q.max:g}" if q.max is not None else ""
                bound = "above" if q.exclusive else "from"
                add("BP-006", where, f"'{v.name}' runs from {v.min:g} to {v.max:g}, outside the domain of {model.export_name} ({bound} {q.min:g}{top}).", "Keep the range inside the model's domain.")


def _bp007(bp: Blueprint, manifest: Manifest, stored_ids, add) -> None:
    """BP-007: named Kit parts and stored Environments exist. Argument signatures are checked by the Build Script validator."""
    for i, a in enumerate(bp.assists):
        where = f"assists[{i}]"
        if a.kind == "kit-part" and not manifest.has(a.id):
            add("BP-007", where, f"The Kit has no part '{a.id}'.", "Name a part from the Kit list, or remove this assist and write it from scratch.")
        elif a.kind == "stored-environment" and a.id not in stored_ids:
            add("BP-007", where, f"There is no stored Environment '{a.id}'.", "Name one of the stored Environments offered, or remove this assist.")
        elif a.kind == "saved-part":
            add("BP-007", where, "There are no saved parts yet.", "Remove this assist; the writer will write the part.")


def _bp008(bp: Blueprint, add) -> None:
    """BP-008: each expected behaviour is one of the testable forms and refers to declared variables."""
    roles = {v.name: v for v in bp.variables}
    for i, b in enumerate(bp.expectedBehaviour):
        where = f"expectedBehaviour[{i}]"
        m = roles.get(b.measured)
        if m is None or m.role != "measured":
            add("BP-008", f"{where}.measured", f"'{b.measured}' is not a measured variable.", "Name a variable whose role is 'measured'.")
        if not b.text.strip():
            add("BP-008", f"{where}.text", "The behaviour has no statement.", "Write it in the student's words, for example 'extension rises as the load rises'.")
        if b.kind == "stays-within":
            if not (_finite(b.low) and _finite(b.high)) or b.low > b.high:  # type: ignore[operator]
                add("BP-008", where, "'stays-within' needs low and high, with low not above high.", "Give both bounds as numbers.")
            continue
        v = roles.get(b.variable)
        if v is None or v.role != "changed":
            add("BP-008", f"{where}.variable", f"'{b.variable}' is not a variable the student changes.", "Sweep a variable whose role is 'changed'.")
        if b.kind == "equals-at":
            if not (_finite(b.at) and _finite(b.value)):
                add("BP-008", where, "'equals-at' needs both 'at' and 'value'.", "Say where the variable is set and what the measured value is there.")
            elif v is not None and _finite(v.min) and _finite(v.max) and not v.min <= b.at <= v.max:  # type: ignore[operator]
                add("BP-008", f"{where}.at", f"{b.at:g} is outside '{v.name}' ({v.min:g} to {v.max:g}).", "Choose a point inside the range.")


def _bp009(bp: Blueprint, add) -> None:
    """BP-009: at least two expected behaviours, three or four steps, and a prediction with two to four choices."""
    if len(bp.expectedBehaviour) < 2:
        add("BP-009", "expectedBehaviour", f"There are {len(bp.expectedBehaviour)} expected behaviours; at least 2 are needed.", "Add statements the checker can test, such as 'rises with' or 'independent of'.")
    if not 3 <= len(bp.steps) <= 4:
        add("BP-009", "steps", f"There are {len(bp.steps)} steps.", "Write 3 or 4 steps, each naming what to drag or drop and what to watch.")
    p = bp.predict
    if not p.question.strip():
        add("BP-009", "predict.question", "The prediction has no question.", "Write a question the student can answer before they try.")
    choices = [c for c in p.choices if c.strip()]
    if not 2 <= len(choices) <= 4:
        add("BP-009", "predict.choices", f"The prediction has {len(choices)} choices.", "Give 2 to 4 choices.")
    if not p.check.strip():
        add("BP-009", "predict.check", "The prediction says nothing about how to check it.", "Say what to do to see the answer.")


def _bp010(bp: Blueprint, add) -> None:
    """BP-010 (V5-D23): the scene states its apparatus and what fills the bench, and the apparatus takes enough of it."""
    s = bp.scene
    if not s.apparatus.strip():
        add("BP-010", "scene.apparatus", "The scene names no apparatus.", "Say what the bench draws.")
    for name, share, floor in (("widthShare", s.widthShare, MIN_WIDTH_SHARE), ("heightShare", s.heightShare, MIN_HEIGHT_SHARE)):
        if not _finite(share) or not 0 < share <= 1:
            add("BP-010", f"scene.{name}", f"{name} is {share}, which is not a share between 0 and 1.", "Give a fraction such as 0.7.")
        elif share < floor:
            what = "width" if name == "widthShare" else "height"
            add("BP-010", f"scene.{name}", f"The apparatus takes {share:.0%} of the bench {what}; at least {floor:.0%} is needed.", f"Draw the apparatus larger, or choose a larger apparatus, so it fills at least {floor:.0%} of the {what}.")
    if not [f for f in s.fills if f.strip()]:
        add("BP-010", "scene.fills", "Nothing is said to fill the rest of the bench.", "Name what fills it: a scale, an axis, a reference object, a backdrop element.")
    if not s.wideScreen.strip():
        add("BP-010", "scene.wideScreen", "The scene does not say how a wide screen is used.", "Say how the bench uses a wide screen so no region is left empty.")
