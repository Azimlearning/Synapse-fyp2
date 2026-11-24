"""The Build Script as typed data (build-script.md). Internal to the API: it is the writer's reply, parsed, and does not cross the wire."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from api.pipeline.free_house import Control

SECTIONS = (
    "BASE", "TITLE", "KICKER", "TRY", "PREDICT", "IDEA", "STEPS", "PARTS", "CONTROLS", "FORMULAS", "READOUTS",
    "STYLE", "DRAWING", "SCRIPT", "HINTS", "EXPLAIN", "TWISTS", "END",
)  # fmt: skip
"""The streaming order (section 2). A reply may leave out an optional section but may not reorder them."""
REQUIRED = ("TITLE", "KICKER", "TRY", "PREDICT", "IDEA", "STEPS", "PARTS", "READOUTS", "HINTS", "EXPLAIN", "END")
LINE_SECTIONS = frozenset({"PARTS", "CONTROLS", "FORMULAS", "READOUTS"})
"""Sections whose every line is a unit complete on its own."""
LIST_SECTIONS = frozenset({"STEPS", "HINTS", "TWISTS"})
CODE_SECTIONS = frozenset({"STYLE", "DRAWING", "SCRIPT"})

MAX_PARTS = 8
MAX_FORMULAS = 10
MAX_READOUTS = 6
MAX_CONTROLS = 4


@dataclass(frozen=True)
class PartLine:
    name: str
    component: str
    args: dict[str, Any]


@dataclass(frozen=True)
class FormulaLine:
    name: str
    expr: str
    unit: str | None


@dataclass(frozen=True)
class ReadoutLine:
    id: str
    label: str
    source: str
    """A control, part or formula name, or `script` when the model's script feeds it through `host.readout`."""
    decimals: int


@dataclass(frozen=True)
class Unit:
    """One complete piece of a reply: a whole text or code section, or one line of a line section."""

    section: str
    text: str
    index: int = 0


@dataclass(frozen=True)
class BuildScript:
    base: str | None
    title: str
    kicker: str
    try_this: str
    predict: tuple[str, list[str], str] | None
    idea: list[str]
    steps: list[str]
    parts: list[PartLine]
    controls: list[Control]
    formulas: list[FormulaLine]
    readouts: list[ReadoutLine]
    style: str
    drawing: str
    script: str
    hints: list[str]
    explain: list[str]
    twists: list[str] = field(default_factory=list)
