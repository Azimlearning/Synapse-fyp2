"""The Build Script parser and unit splitter (build-script.md sections 2 to 5).

`units(raw)` yields each piece of a reply that is complete on its own, in the order it arrives, and stops at a partial one: this is what the per-unit validator
reads while a reply streams. `parse(raw)` reads a whole reply into a `BuildScript`, or returns the reason it is not one (told to the writer on its retry, in
the same style as `free_house.parse`).

Nothing here checks meaning. A line is well formed or it is not; whether a part exists, a formula's units fit, or a drawing is safe is `validate`'s job.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator

from api.buildscript.model import (
    LINE_SECTIONS,
    MAX_CONTROLS,
    MAX_FORMULAS,
    MAX_PARTS,
    MAX_READOUTS,
    REQUIRED,
    SECTIONS,
    BuildScript,
    FormulaLine,
    PartLine,
    ReadoutLine,
    Unit,
)
from api.pipeline.free_house import _ID, Control, _number

_MARK = re.compile(r"^@@([A-Za-z]+)[ \t]*$", re.MULTILINE)
_PART = re.compile(r"^([A-Za-z][A-Za-z0-9_]{0,39})\s*=\s*([A-Za-z][A-Za-z0-9_.]*)\s*(\{.*\})?\s*$", re.DOTALL)
_FORMULA = re.compile(r"^([A-Za-z][A-Za-z0-9_]{0,39})\s*=\s*(.+?)\s*(?:\[([^\]]*)\])?\s*$")


def _norm(raw: str) -> str:
    return raw.replace("\r\n", "\n")


def _lines(text: str) -> list[str]:
    return [" ".join(line.split()) for line in text.splitlines() if line.strip()]


def _items(text: str) -> list[str]:
    return [re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line) for line in _lines(text)]


def _split(text: str) -> list[tuple[str, str]]:
    """(marker, body) for every marker line, in order. The body is everything up to the next marker, trimmed of blank lines at both ends."""
    marks = list(_MARK.finditer(text))
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((m.group(1), text[m.end() : end].strip("\n")))
    return out


def units(raw: str) -> Iterator[Unit]:
    """Every complete unit so far. A section is complete once the next marker has begun (or it is `@@END`); a line of PARTS, CONTROLS, FORMULAS or READOUTS is
    complete once a newline follows it, so a half-written line is never yielded."""
    text = _norm(raw)
    marks = list(_MARK.finditer(text))
    for i, m in enumerate(marks):
        name = m.group(1)
        last = i == len(marks) - 1
        body = text[m.end() : (marks[i + 1].start() if not last else len(text))]
        if name == "END":
            yield Unit("END", "", 0)
            return
        if name in LINE_SECTIONS:
            pieces = body.split("\n")
            if last:
                pieces = pieces[:-1]  # the last piece has no newline after it yet
            n = 0
            for line in pieces:
                if line.strip() and not (name == "PARTS" and line.strip().lower() == "none"):
                    yield Unit(name, line.strip(), n)
                    n += 1
        elif not last:
            yield Unit(name, body.strip("\n"), 0)


def parse_part(line: str) -> PartLine | str:
    m = _PART.match(line.strip())
    if not m:
        return f"a @@PARTS line is not 'name = component {{ JSON arguments }}': {line[:80]}"
    args: object = {}
    if m.group(3):
        try:
            args = json.loads(m.group(3))
        except json.JSONDecodeError:
            return f"the arguments of the part '{m.group(1)}' are not valid JSON: {m.group(3)[:80]}"
    if not isinstance(args, dict):
        return f"the arguments of the part '{m.group(1)}' must be a JSON object"
    return PartLine(m.group(1), m.group(2), args)


def parse_control(line: str) -> Control | str:
    parts = [p.strip() for p in line.split("|")]
    if len(parts) != 7 or not _ID.fullmatch(parts[0]):
        return f"a @@CONTROLS line is not 'id | label | min | max | step | start | unit': {line[:80]}"
    try:
        lo, hi, step, value = (_number(p) for p in parts[2:6])
    except ValueError:
        return f"a @@CONTROLS line has a value that is not a number: {line[:80]}"
    if not (lo < hi and step > 0 and lo <= value <= hi):
        return f"the control '{parts[0]}' needs min < max, a step above 0 and a start inside the range"
    return Control(parts[0], parts[1][:60] or parts[0], lo, hi, step, value, parts[6][:20])


def parse_formula(line: str) -> FormulaLine | str:
    m = _FORMULA.match(line.strip())
    if not m:
        return f"a @@FORMULAS line is not 'name = expression [unit]': {line[:80]}"
    return FormulaLine(m.group(1), m.group(2).strip(), m.group(3).strip() if m.group(3) is not None else None)


def parse_readout(line: str) -> ReadoutLine | str:
    parts = [p.strip() for p in line.split("|")]
    if len(parts) != 4 or not _ID.fullmatch(parts[0]):
        return f"a @@READOUTS line is not 'id | label with unit | source | decimals': {line[:80]}"
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", parts[2]):
        return f"the source of the readout '{parts[0]}' must be a control, part or formula name, or 'script'"
    if not re.fullmatch(r"\d", parts[3]):
        return f"the decimals of the readout '{parts[0]}' must be a whole number from 0 to 9"
    return ReadoutLine(parts[0], parts[1][:60] or parts[0], parts[2], int(parts[3]))


def _predict(text: str) -> tuple[str, list[str], str] | None:
    lines = _lines(text)
    choices = [re.sub(r"^\s*[-*•]\s*", "", x) for x in lines if re.match(r"^\s*[-*•]", x)]
    reveal = next((x.split(":", 1)[1].strip() for x in lines if x.lower().startswith("check:")), "")
    question = next((x for x in lines if not re.match(r"^\s*[-*•]", x) and not x.lower().startswith("check:")), "")
    return (question, choices[:4], reveal) if question and choices else None


def parse(raw: str) -> BuildScript | str:
    """The Build Script, or the reason the reply is not one."""
    text = _norm(raw)
    pairs = _split(text)
    seen: dict[str, str] = {}
    last_rank = -1
    for name, body in pairs:
        if name not in SECTIONS:
            return f"@@{name} is not a section of the Build Script (the sections are {', '.join('@@' + s for s in SECTIONS)})"
        if name in seen:
            return f"@@{name} appears twice"
        rank = SECTIONS.index(name)
        if rank < last_rank:
            return f"@@{name} is out of order: the sections go {' then '.join('@@' + s for s in SECTIONS)}"
        last_rank = rank
        seen[name] = body
    missing = [n for n in REQUIRED if n not in seen]
    if missing:
        if missing == ["END"]:
            return "the reply stopped before @@END (it was cut off); write a shorter Environment"
        return "the reply is missing these sections: " + ", ".join("@@" + m for m in missing)

    def lines_of(section: str) -> list[str]:
        return [ln.strip() for ln in seen.get(section, "").splitlines() if ln.strip()]

    title = _lines(seen["TITLE"])
    if not title:
        return "@@TITLE is empty"
    parts: list[PartLine] = []
    body = lines_of("PARTS")
    for ln in [] if [b.lower() for b in body] == ["none"] else body:
        p = parse_part(ln)
        if isinstance(p, str):
            return p
        parts.append(p)
    controls: list[Control] = []
    for ln in lines_of("CONTROLS"):
        c = parse_control(ln)
        if isinstance(c, str):
            return c
        controls.append(c)
    formulas: list[FormulaLine] = []
    for ln in lines_of("FORMULAS"):
        f = parse_formula(ln)
        if isinstance(f, str):
            return f
        formulas.append(f)
    readouts: list[ReadoutLine] = []
    for ln in lines_of("READOUTS"):
        r = parse_readout(ln)
        if isinstance(r, str):
            return r
        readouts.append(r)
    for label, got, limit in (("PARTS", parts, MAX_PARTS), ("CONTROLS", controls, MAX_CONTROLS), ("FORMULAS", formulas, MAX_FORMULAS), ("READOUTS", readouts, MAX_READOUTS)):
        if len(got) > limit:
            return f"@@{label} lists {len(got)} lines; the most is {limit}"
    ids = [c.id for c in controls] + [p.name for p in parts] + [f.name for f in formulas] + [r.id for r in readouts]
    if len(set(ids)) != len(ids):
        return "every control, part, formula and readout needs its own name"
    base = _lines(seen.get("BASE", ""))
    return BuildScript(
        base=None if not base or base[0].lower() == "none" else base[0],
        title=title[0],
        kicker=(_lines(seen["KICKER"]) or [""])[0],
        try_this=" ".join(_lines(seen["TRY"])),
        predict=_predict(seen["PREDICT"]),
        idea=_lines(seen["IDEA"]),
        steps=_items(seen["STEPS"]),
        parts=parts,
        controls=controls,
        formulas=formulas,
        readouts=readouts,
        style=seen.get("STYLE", "").strip(),
        drawing=seen.get("DRAWING", "").strip(),
        script=seen.get("SCRIPT", "").strip("\n"),
        hints=_items(seen["HINTS"]),
        explain=[" ".join(p.split()) for p in re.split(r"\n\s*\n", seen["EXPLAIN"]) if p.strip()],
        twists=_items(seen.get("TWISTS", "")),
    )

