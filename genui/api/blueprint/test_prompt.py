"""The Blueprint prompt pack stays in step with the wire type and the checker's rules."""

from __future__ import annotations

import json
import re

from api import prompts
from api.blueprint.checks import MAX_CHANGED, MIN_HEIGHT_SHARE, MIN_WIDTH_SHARE
from api.schema.generated import Blueprint


def _example() -> dict:
    body = prompts.load("blueprint").stable
    start = body.index("{\n")
    depth, end = 0, start
    for i in range(start, len(body)):
        depth += {"{": 1, "}": -1}.get(body[i], 0)
        if depth == 0:
            end = i + 1
            break
    return json.loads(body[start:end])


def test_the_pack_loads_with_its_declared_inputs_and_stays_in_budget() -> None:
    p = prompts.load("blueprint")
    assert p.version >= 1 and p.inputs == ("question", "offers")
    assert prompts.estimate_tokens(p.stable) <= p.budget
    assert "—" not in p.body and "–" not in p.body


def test_the_example_has_exactly_the_wire_type_s_fields() -> None:
    ex = _example()
    assert set(ex) == set(Blueprint.model_fields)
    nested = {
        "variables": "BlueprintVariable",
        "interactions": "BlueprintInteraction",
        "expectedBehaviour": "BlueprintBehaviour",
        "assists": "BlueprintAssist",
    }
    import api.schema.generated as g

    for field, model in nested.items():
        assert set(ex[field][0]) == set(getattr(g, model).model_fields), field
    assert set(ex["scene"]) == set(g.BlueprintScene.model_fields)
    assert set(ex["predict"]) == set(g.BlueprintPredict.model_fields)


def test_the_rules_the_pack_states_are_the_checkers_numbers() -> None:
    text = prompts.load("blueprint").stable
    words = {3: "three", 4: "four", 5: "five", 6: "six"}
    assert f"At most {words[MAX_CHANGED]} are" in text, "the pack and MAX_CHANGED disagree"
    assert str(MIN_WIDTH_SHARE) in text and str(MIN_HEIGHT_SHARE) in text
    for gesture in ("drag", "drop", "rotate", "pour", "press-hold", "pinch"):
        assert f'"{gesture}"' in text
    for kind in ("rises-with", "falls-with", "independent-of", "stays-within", "equals-at"):
        assert f'"{kind}"' in text


def test_the_variable_part_carries_the_question_and_the_offers() -> None:
    p = prompts.load("blueprint")
    system, user = p.render_parts(question="Why does a spring stretch?", offers="- massHanger")
    assert "Why does a spring stretch?" in user and "- massHanger" in user
    assert not re.search(r"\{\{\w+\}\}", system + user)
