"""The Build Script validator (build-script.md section 9): each unit is checked as it arrives, against the units before it, so a reply can be stopped at the first
fault and sent back with the reason in the checker's words.

Rule ids are `BS-001` onward (the Blueprint's are `BP-`, v4's plan rules `PLAN-`):

| Id | Unit |
|---|---|
| BS-000 | the reply is not a Build Script at all (`parse` refuses it) |
| BS-001 | a text section: plain words, lengths, counts, no long dashes |
| BS-002 | a PARTS line: a Kit part that exists, its arguments, backward references, a science model's domain |
| BS-003 | a CONTROLS line: ids, ranges, the textbook's constants |
| BS-004 | a FORMULAS line: grammar, names defined earlier, units |
| BS-005 | a READOUTS line: a source that exists, the unit stated |
| BS-006 | STYLE and DRAWING: selector scope, motion only where motion is allowed, the v4 scans, size |
| BS-007 | SCRIPT: the v4 scans, the `host` API, no direct write to a readout |
| BS-008 | the whole reply: every control has a handle and changes something, every readout has a source |

Nothing here makes a page safe or correct. The assembled page still goes through the post-processor, the L0 scan, the second reader and the real browser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from api.blueprint.checks import Finding
from api.buildscript import formula as fm
from api.buildscript.model import (
    MAX_CONTROLS,
    MAX_FORMULAS,
    MAX_PARTS,
    MAX_READOUTS,
    BuildScript,
    Unit,
)
from api.buildscript.parse import parse, parse_control, parse_formula, parse_part, parse_readout, units
from api.kitmanifest import Manifest
from api.pipeline import constants
from api.verify.scan import forbidden_api_scan, free_lane_scan

MAX_SCRIPT = 12000
MAX_DRAWING = 12000
MAX_STYLE = 6000
MAX_TEXT = 400
LONG_DASHES = ("—", "–")
HOST_API = frozenset({"value", "on", "set", "found", "readout", "reducedMotion"})
RESERVED_NAMES = fm.RESERVED | {"host", "script", "found", "bench"}
_TAG = re.compile(r"<\s*/?\s*[A-Za-z!]")
_MARKDOWN = re.compile(r"`|\*\*|^\s*#{1,6}\s", re.MULTILINE)
_REF = re.compile(r"^\$([A-Za-z][A-Za-z0-9_]*)$")


@dataclass(frozen=True)
class Symbol:
    kind: str  # control | part | formula
    unit_text: str | None
    unit: fm.Unit | None


class Validator:
    """Feed it each unit in order. `feed` returns that unit's findings; `finish` runs the whole-reply checks on the parsed script."""

    def __init__(self, manifest: Manifest, stored_ids: frozenset[str] | set[str] | None = None) -> None:
        self.manifest = manifest
        self.stored_ids = stored_ids
        self.scope: dict[str, Symbol] = {}
        self.used: set[str] = set()
        self.readout_ids: list[str] = []
        self.readout_sources: dict[str, str] = {}
        self.counts = {"PARTS": 0, "CONTROLS": 0, "FORMULAS": 0, "READOUTS": 0}

    # ── per unit ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    def feed(self, u: Unit) -> list[Finding]:
        path = f"@@{u.section}" + (f"[{u.index}]" if u.section in self.counts else "")
        out: list[Finding] = []

        def add(rule: str, reason: str, fix: str) -> None:
            out.append(Finding(rule, path, reason, fix))

        s = u.section
        if s in self.counts:
            self.counts[s] += 1
        if s in ("BASE", "TITLE", "KICKER", "TRY", "PREDICT", "IDEA", "STEPS", "HINTS", "EXPLAIN", "TWISTS"):
            self._text(u, add)
        elif s == "PARTS":
            self._part(u.text, add)
        elif s == "CONTROLS":
            self._control(u.text, add)
        elif s == "FORMULAS":
            self._formula(u.text, add)
        elif s == "READOUTS":
            self._readout(u.text, add)
        elif s == "STYLE":
            self._style(u.text, add)
        elif s == "DRAWING":
            self._drawing(u.text, add)
        elif s == "SCRIPT":
            self._script(u.text, add)
        limits = {"PARTS": MAX_PARTS, "CONTROLS": MAX_CONTROLS, "FORMULAS": MAX_FORMULAS, "READOUTS": MAX_READOUTS}
        if s in limits and self.counts[s] > limits[s]:
            add("BS-001", f"@@{s} has more than {limits[s]} lines.", f"Keep at most {limits[s]}.")
        return out

    # ── text sections (BS-001) ───────────────────────────────────────────────────────────────────────────────────────────
    def _text(self, u: Unit, add) -> None:
        t, s = u.text, u.section
        if not t.strip():
            add("BS-001", f"@@{s} is empty.", f"Write @@{s}.")
            return
        if any(d in t for d in LONG_DASHES):
            add("BS-001", f"@@{s} has a long dash.", "Use a comma, a colon or a new sentence, and 'to' for a range.")
        if _TAG.search(t) or _MARKDOWN.search(t):
            add("BS-001", f"@@{s} is not plain text: it has markup or markdown.", "Write plain words and plain punctuation only.")
        lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
        if s in ("TITLE", "KICKER") and (len(lines) != 1 or len(lines[0]) > 60):
            add("BS-001", f"@@{s} must be one line of at most 60 characters.", "Shorten it.")
        if s == "BASE" and len(lines) != 1:
            add("BS-001", "@@BASE must be one id or 'none'.", "Write one id, or none.")
        if s == "BASE" and lines and lines[0].lower() != "none" and self.stored_ids is not None and lines[0] not in self.stored_ids:
            add("BS-001", f"There is no stored Environment '{lines[0]}'.", "Name one of the offered Environments, or write none.")
        if s != "EXPLAIN" and any(len(ln) > MAX_TEXT for ln in lines):
            add("BS-001", f"A line of @@{s} is over {MAX_TEXT} characters.", "Shorten it.")
        if s == "TRY" and len(lines) != 1:
            add("BS-001", "@@TRY is one sentence.", "Say what to drag or drop first, in one sentence.")
        counts = {"STEPS": (3, 4), "HINTS": (2, 3), "TWISTS": (2, 3), "IDEA": (1, 3)}
        if s in counts:
            n = len(lines)
            lo, hi = counts[s]
            if not lo <= n <= hi:
                add("BS-001", f"@@{s} has {n} lines; it needs {lo} to {hi}.", f"Write {lo} to {hi}.")
        if s == "EXPLAIN":
            n = len([p for p in re.split(r"\n\s*\n", t) if p.strip()])
            if not 2 <= n <= 3:
                add("BS-001", f"@@EXPLAIN has {n} paragraphs; it needs 2 or 3.", "Write 2 or 3 short paragraphs separated by a blank line.")
        if s == "PREDICT":
            choices = [ln for ln in lines if re.match(r"^[-*•]", ln)]
            check = [ln for ln in lines if ln.lower().startswith("check:")]
            question = [ln for ln in lines if ln not in choices and ln not in check]
            if len(question) < 1 or not 2 <= len(choices) <= 4 or len(check) != 1:
                add("BS-001", "@@PREDICT needs a question, 2 to 4 '- choice' lines and one 'Check: ...' line.", "Follow that shape.")

    # ── PARTS (BS-002) ───────────────────────────────────────────────────────────────────────────────────────────────────
    def _define(self, name: str, kind: str, unit_text: str | None, unit: fm.Unit | None, add, rule: str) -> bool:
        if name in RESERVED_NAMES:
            add(rule, f"'{name}' is a reserved word (a function, constant or part of the page).", "Choose another name.")
            return False
        if name in self.used:
            add(rule, f"The name '{name}' is already used.", "Give every control, part, formula and readout its own name.")
            return False
        self.used.add(name)
        if kind != "readout":
            self.scope[name] = Symbol(kind, unit_text, unit)
        return True

    def _part(self, line: str, add) -> None:
        p = parse_part(line)
        if isinstance(p, str):
            add("BS-002", p, "Write 'name = component { JSON arguments }'.")
            return
        if p.component.startswith("saved."):
            add("BS-002", "There are no saved parts yet.", "Use a Kit part, or write it yourself.")
            return
        entry = self.manifest.components.get(p.component)
        if entry is None:
            add("BS-002", f"The Kit has no part '{p.component}'.", "Use a part from the Kit list, or write the part yourself.")
            return
        for value in p.args.values():
            for ref in _refs(value):
                if ref not in self.scope:
                    add("BS-002", f"'${ref}' in {p.name} is not defined before this line.", "Refer only to a control, part or formula written earlier.")
        want = _signature_args(entry.get("signature", ""))
        if want is not None:
            required, optional = want
            for key in p.args:
                if key not in required | optional:
                    add("BS-002", f"The part {p.component} has no argument '{key}'.", f"Its arguments are {sorted(required | optional)}.")
            for key in required - set(p.args):
                add("BS-002", f"The part {p.component} needs the argument '{key}'.", f"Give {key}.")
        model = self.manifest.models.get(entry["modelId"]) if entry.get("modelId") else None
        if model is not None:
            for key, value in p.args.items():
                q = model.inputs.get(key) or model.params.get(key)
                if q is not None and isinstance(value, int | float) and not isinstance(value, bool):
                    bad = value < q.min or (q.exclusive and value <= q.min) or (q.max is not None and (value > q.max or (q.max_exclusive and value >= q.max)))
                    if bad:
                        add("BS-002", f"{key}={value:g} is outside the domain of {p.component} (a {q.unit} from {q.min:g}).", "Keep the value inside the model's domain.")
        unit_text = model.output_unit if model is not None else None
        self._define(p.name, "part", unit_text, fm.parse_unit(unit_text) if unit_text is not None else None, add, "BS-002")

    # ── CONTROLS (BS-003) ────────────────────────────────────────────────────────────────────────────────────────────────
    def _control(self, line: str, add) -> None:
        c = parse_control(line)
        if isinstance(c, str):
            add("BS-003", c, "Write 'id | label | min | max | step | start | unit'.")
            return
        known = constants.find(None, None, ident=c.id)
        if known is not None and not constants.is_accepted(known, c.value):
            add("BS-003", f"The control '{c.id}' starts at {c.value:g}, and the textbooks use {constants.accepted_text(known)} for the {known.name}.", f"Start it at {constants.accepted_text(known)}.")
        self._define(c.id, "control", c.unit, fm.parse_unit(c.unit), add, "BS-003")

    # ── FORMULAS (BS-004) ────────────────────────────────────────────────────────────────────────────────────────────────
    def _formula(self, line: str, add) -> None:
        f = parse_formula(line)
        if isinstance(f, str):
            add("BS-004", f, "Write 'name = expression [unit]'.")
            return
        try:
            tree = fm.parse(f.expr)
        except fm.FormulaError as exc:
            add("BS-004", f"{f.name}: {exc}.", "Rewrite it in the allowed grammar.")
            return
        unknown = sorted(fm.free_names(tree) - set(self.scope))
        for n in unknown:
            add("BS-004", f"{f.name} uses '{n}', which is not a control, part or formula written before it.", "Define it earlier, or use a name that exists.")
        if unknown:
            return
        units = {n: s.unit for n, s in self.scope.items()}
        try:
            fm.check_units(tree, units, f.unit)
        except fm.FormulaError as exc:
            add("BS-004", f"{f.name}: {exc}.", "Fix the units, or convert a quantity first.")
        got = f.unit if f.unit is not None else None
        unit = fm.parse_unit(f.unit) if f.unit is not None else _safe_unit(tree, units)
        self._define(f.name, "formula", got, unit, add, "BS-004")

    # ── READOUTS (BS-005) ────────────────────────────────────────────────────────────────────────────────────────────────
    def _readout(self, line: str, add) -> None:
        r = parse_readout(line)
        if isinstance(r, str):
            add("BS-005", r, "Write 'id | label with its unit | source | decimals'.")
            return
        if r.source != "script" and r.source not in self.scope:
            add("BS-005", f"The readout '{r.id}' reads '{r.source}', which is not a control, part or formula written before it.", "Name a source that exists, or 'script' if your script feeds it.")
        elif r.source in self.scope:
            sym = self.scope[r.source]
            if sym.unit_text and sym.unit_text != "planet" and sym.unit_text not in r.label:
                add("BS-005", f"The label of '{r.id}' does not show its unit ({sym.unit_text}).", f"Write the unit in the label, for example 'Weight ({sym.unit_text})'.")
        if any(d in r.label for d in LONG_DASHES) or _TAG.search(r.label):
            add("BS-005", f"The label of '{r.id}' has markup or a long dash.", "Use plain words.")
        if self._define(r.id, "readout", None, None, add, "BS-005"):
            self.readout_ids.append(r.id)
            self.readout_sources[r.id] = r.source

    # ── STYLE and DRAWING (BS-006) ───────────────────────────────────────────────────────────────────────────────────────
    def _style(self, css: str, add) -> None:
        if len(css) > MAX_STYLE:
            add("BS-006", f"@@STYLE is {len(css)} characters, over {MAX_STYLE}.", "Shorten it.")
        if "</" in css or "<" in css:
            add("BS-006", "@@STYLE is plain CSS, without tags.", "Remove the tags.")
        for reason in _css_problems(css):
            add("BS-006", reason, "Scope every selector under #bench-art and keep motion inside @media (prefers-reduced-motion: no-preference).")
        _scans(css, add, "BS-006", "@@STYLE")

    def _drawing(self, svg: str, add) -> None:
        if len(svg) > MAX_DRAWING:
            add("BS-006", f"@@DRAWING is {len(svg)} characters, over {MAX_DRAWING}.", "Draw repeated shapes in the script with a loop.")
        if len(re.findall(r"<\s*svg\b", svg, re.IGNORECASE)) != 1 or not re.search(r"<\s*svg\b[^>]*\bid\s*=\s*[\"']bench-art[\"']", svg, re.IGNORECASE):
            add("BS-006", "@@DRAWING must be exactly one <svg id=\"bench-art\">.", "Write one svg with id bench-art.")
        elif not re.search(r"<\s*svg\b[^>]*\bviewBox\s*=", svg, re.IGNORECASE) or not re.search(r"<\s*svg\b[^>]*\baria-label\s*=", svg, re.IGNORECASE):
            add("BS-006", "The svg needs a viewBox and an aria-label (its text equivalent).", "Add viewBox and aria-label.")
        if re.search(r"<\s*/?\s*(script|style)\b", svg, re.IGNORECASE):
            add("BS-006", "@@DRAWING must not contain <script> or <style>.", "Put code in @@SCRIPT and CSS in @@STYLE.")
        if re.search(r"<\s*(image|foreignObject)\b", svg, re.IGNORECASE):
            add("BS-006", "@@DRAWING must not contain <image> or <foreignObject>: they load or embed outside content.", "Draw with shapes, paths and text only.")
        _scans(svg, add, "BS-006", "@@DRAWING")

    # ── SCRIPT (BS-007) ──────────────────────────────────────────────────────────────────────────────────────────────────
    def _script(self, code: str, add) -> None:
        if len(code) > MAX_SCRIPT:
            add("BS-007", f"@@SCRIPT is {len(code)} characters, over {MAX_SCRIPT}.", "Shorten it: draw repeated shapes in a loop.")
        if re.search(r"<\s*/?\s*(script|style)\b", code, re.IGNORECASE):
            add("BS-007", "@@SCRIPT is plain JavaScript, without tags.", "Remove the tags.")
        _scans(code, add, "BS-007", "@@SCRIPT")
        for call in sorted(set(re.findall(r"\bhost\s*\.\s*([A-Za-z_]\w*)", code)) - HOST_API):
            add("BS-007", f"host.{call} does not exist.", f"The host offers {', '.join('host.' + a for a in sorted(HOST_API))}.")
        for rid in self.readout_ids:
            q = re.escape(rid)
            if re.search(rf"getElementById\s*\(\s*[\"']{q}[\"']|querySelector(?:All)?\s*\(\s*[\"'][^\"']*(?:#{q}\b|\[data-synapse-readout)", code) or "data-synapse-readout" in code:
                add("BS-007", f"The script writes the readout '{rid}' directly.", "Synapse writes every readout. Feed one from script with host.readout(id, value) and a source of 'script'.")
                break
        for rid in re.findall(r"host\s*\.\s*readout\s*\(\s*[\"']([^\"']+)[\"']", code):
            if self.readout_sources.get(rid) != "script":
                add("BS-007", f"host.readout('{rid}', ...) feeds a readout that does not have the source 'script'.", "Declare it in @@READOUTS with the source script.")

    # ── the whole reply (BS-008) ─────────────────────────────────────────────────────────────────────────────────────────
    def finish(self, bs: BuildScript) -> list[Finding]:
        out: list[Finding] = []

        def add(path: str, reason: str, fix: str) -> None:
            out.append(Finding("BS-008", path, reason, fix))

        if not bs.controls:
            add("@@CONTROLS", "The student changes nothing: there is no control.", "Give 1 to 4 controls, each with a handle in the drawing.")
        if not bs.drawing:
            add("@@DRAWING", "There is no drawing.", "Draw the apparatus as one svg with its handles.")
        if not bs.readouts:
            add("@@READOUTS", "There is no readout.", "Give at least one readout.")
        for c in bs.controls:
            handled = f'data-synapse-handle="{c.id}"' in bs.drawing or f"data-synapse-handle='{c.id}'" in bs.drawing or re.search(rf"host\s*\.\s*set\s*\(\s*[\"']{re.escape(c.id)}[\"']", bs.script)
            if not handled:
                add(f"@@CONTROLS {c.id}", f"The control '{c.id}' has no handle in the drawing.", f"Draw a handle marked data-synapse-handle=\"{c.id}\" and drive it with host.set(\"{c.id}\", value).")
        for rid, src in self.readout_sources.items():
            if src == "script" and not re.search(rf"host\s*\.\s*readout\s*\(\s*[\"']{re.escape(rid)}[\"']", bs.script):
                add(f"@@READOUTS {rid}", f"The readout '{rid}' has the source script, but the script never calls host.readout('{rid}', value).", "Feed it, or give it a control or formula as its source.")
        feeds = _reachable(bs)
        for c in bs.controls:
            used_in_script = re.search(rf"host\s*\.\s*(?:value|on)\s*\(\s*[\"']{re.escape(c.id)}[\"']", bs.script)
            if c.id not in feeds and not used_in_script:
                add(f"@@CONTROLS {c.id}", f"The control '{c.id}' changes no readout.", "Use it in a formula that a readout shows, or read it in the script with host.value.")
        return out


def _reachable(bs: BuildScript) -> set[str]:
    """Every name a readout shows, directly or through formulas."""
    deps: dict[str, set[str]] = {}
    for f in bs.formulas:
        try:
            deps[f.name] = fm.free_names(fm.parse(f.expr))
        except fm.FormulaError:
            deps[f.name] = set()
    for p in bs.parts:
        deps[p.name] = {r for v in p.args.values() for r in _refs(v)}
    seen: set[str] = set()
    stack = [r.source for r in bs.readouts if r.source != "script"]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(deps.get(n, ()))
    return seen


def _refs(value: Any) -> list[str]:
    if isinstance(value, str):
        m = _REF.match(value)
        return [m.group(1)] if m else []
    if isinstance(value, list):
        return [r for v in value for r in _refs(v)]
    if isinstance(value, dict):
        return [r for v in value.values() for r in _refs(v)]
    return []


def _safe_unit(tree: fm.Node, units: dict[str, fm.Unit | None]) -> fm.Unit | None:
    try:
        return fm.unit_of(tree, units)
    except fm.FormulaError:
        return None


def _signature_args(sig: str) -> tuple[set[str], set[str]] | None:
    """The argument names of a Kit part from its signature text, `name({a, b?}): T` or `name(env, {a, b?}): T`. None if the signature has no object argument."""
    start = sig.find("{")
    if start < 0:
        return None
    depth, end = 0, -1
    for i in range(start, len(sig)):
        depth += {"{": 1, "}": -1}.get(sig[i], 0)
        if depth == 0:
            end = i
            break
    if end < 0:
        return None
    inner, parts, level, cur = sig[start + 1 : end], [], 0, ""
    for ch in inner:
        level += {"<": 1, "(": 1, "[": 1, "{": 1, ">": -1, ")": -1, "]": -1, "}": -1}.get(ch, 0)
        if ch == "," and level == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    required: set[str] = set()
    optional: set[str] = set()
    for part in parts:
        token = part.split(":")[0].strip()
        if not token:
            continue
        (optional if token.endswith("?") else required).add(token.rstrip("?"))
    return required, optional


def _scans(text: str, add, rule: str, label: str) -> None:
    hit = forbidden_api_scan(text) or free_lane_scan(text)
    if hit is not None:
        add(rule, f"{label}: {hit.reason}.", "Remove it: the sandbox refuses it.")


def _css_problems(css: str) -> list[str]:
    """Selectors outside #bench-art, at-rules that are not allowed, and motion outside a no-preference media query."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    problems: list[str] = []
    stack: list[tuple[str, int]] = []  # (kind, body start)
    nopref = 0
    pos = 0
    for m in re.finditer(r"[{}]", css):
        if m.group() == "{":
            head = css[pos : m.start()].strip()
            pos = m.end()
            if head.startswith("@"):
                at = head.split()[0].lower().lstrip("@").removeprefix("-webkit-")
                if at in ("media", "supports"):
                    stack.append(("at", pos))
                    if re.search(r"prefers-reduced-motion\s*:\s*no-preference", head):
                        nopref += 1
                        stack[-1] = ("nopref", pos)
                elif at == "keyframes":
                    if not nopref:
                        problems.append("@keyframes is outside @media (prefers-reduced-motion: no-preference)")
                    stack.append(("keyframes", pos))
                else:
                    problems.append(f"the at-rule @{at} is not allowed")
                    stack.append(("skip", pos))
            elif stack and stack[-1][0] in ("keyframes", "skip", "frame"):
                stack.append(("frame", pos))
            else:
                for sel in (s.strip() for s in head.split(",")):
                    if sel and not sel.startswith("#bench-art"):
                        problems.append(f"the selector '{sel[:40]}' is not under #bench-art")
                stack.append(("rule", pos))
        else:
            if not stack:
                continue
            kind, start = stack.pop()
            if kind == "nopref":
                nopref -= 1
            if kind == "rule" and not nopref and re.search(r"\b(animation|transition)\b", css[start : m.start()]):
                problems.append("an animation or transition is outside @media (prefers-reduced-motion: no-preference)")
            pos = m.end()
    return problems


def validate(raw: str, manifest: Manifest, stored_ids: frozenset[str] | set[str] | None = None, *, early_stop: bool = True) -> list[Finding]:
    """Every finding for a whole reply. With `early_stop` (the default, as in a live run) the first unit that fails ends the check."""
    parsed = parse(raw)
    if isinstance(parsed, str):
        return [Finding("BS-000", "reply", parsed, "Reply in the labelled sections, in order, ending with @@END.")]
    v = Validator(manifest, stored_ids)
    out: list[Finding] = []
    for unit in units(raw):
        found = v.feed(unit)
        out.extend(found)
        if found and early_stop:
            return out
    return out + v.finish(parsed)

