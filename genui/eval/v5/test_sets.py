"""The v5 question sets: right sizes, unique ids, every pin matches, drafts are unapproved so no live run can use them, and the sets hold what the evaluation plan says."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.v5 import sets

LONG_DASHES = ("—", "–")


def data(name: str) -> dict:
    return json.loads(sets.path(name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", sets.NAMES)
def test_each_set_has_its_size_unique_ids_and_no_long_dash(name: str) -> None:
    d = data(name)
    ids = [q["id"] for q in d["questions"]]
    assert len(ids) == sets.SIZES[name] and len(set(ids)) == len(ids)
    assert all(q["question"].strip().endswith(("?", ".")) for q in d["questions"])
    assert not any(x in sets.path(name).read_text(encoding="utf-8") for x in LONG_DASHES)
    assert d["set"] == name


@pytest.mark.parametrize("name", sets.NAMES)
def test_each_set_is_pinned_and_a_draft_is_refused_by_a_live_run(name: str) -> None:
    assert sets.pinned(name), f"{name} no longer matches its pin: if the change is meant, it is a declared amendment (pin it and say so in the changelog)"
    if not data(name)["approved"]:
        assert "not approved" in str(sets.load(name))


def test_a_changed_or_unpinned_set_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sets, "HERE", tmp_path)
    (tmp_path / "W.json").write_text(json.dumps({"set": "W", "approved": True, "questions": []}), encoding="utf-8")
    assert "does not match its pinned hash" in str(sets.load("W"))  # no pin yet
    sets.pin_path("W").write_text(sets.digest(sets.path("W")) + "\n", encoding="utf-8")
    assert isinstance(sets.load("W"), dict)
    sets.path("W").write_text(json.dumps({"set": "W", "approved": True, "questions": [1]}), encoding="utf-8")
    assert "does not match its pinned hash" in str(sets.load("W"))


def test_set_r_is_exactly_the_questions_the_library_remembers() -> None:
    library = json.loads(sets.LIBRARY_QUESTIONS.read_text(encoding="utf-8"))
    remembered = [q for k, qs in library.items() if not k.startswith("_") for q in qs]
    assert [q["question"] for q in data("R")["questions"]] == remembered
    assert data("R") == sets.make_r() | {"questions": data("R")["questions"]}


def test_the_gate_set_is_three_twists_none_of_which_is_the_writer_prompts_worked_example() -> None:
    gate = [q["question"] for q in data("T-gate")["questions"]]
    assert gate == [q["question"] for q in data("T")["questions"][:3]], "the gate set is the first three of T"
    for q in gate:
        assert "series" not in q.lower() or "spring" not in q.lower(), "the worked example in the writer prompt is two springs in series"


def test_set_f_items_name_a_base_question_and_a_change() -> None:
    for q in data("F")["questions"]:
        assert q["question"].strip() and q["change"].strip()


def test_no_set_shares_a_question_with_another_except_t_gate_and_t() -> None:
    seen: dict[str, str] = {}
    for name in ("R", "T", "N", "W"):
        for q in data(name)["questions"]:
            assert q["question"] not in seen, f"{q['question']} is in both {seen.get(q['question'])} and {name}"
            seen[q["question"]] = name


def test_the_status_report_lists_every_set() -> None:
    rows = sets.status()
    assert [r["set"] for r in rows] == list(sets.NAMES) and all(r["present"] and r["pinned"] for r in rows)
