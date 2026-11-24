"""V5-D22: the chains file. A paid id in a free chain is the one mistake that would spend money outside the ledger, so it is refused at load."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.llm.chains import DEFAULT_PATH, MAX_CHAIN, ChainsError, load_chains, parse_chains

GOOD = {
    "chains": {"fast": ["a/x:free", "b/y:free"], "build": ["c/z:free"]},
    "purposes": {"route": "fast", "plan": "build"},
    "default": "fast",
}


def test_the_shipped_chains_file_loads_and_every_purpose_the_pipeline_uses_has_a_chain() -> None:
    chains = load_chains()
    assert chains.first().endswith(":free")
    for purpose in ("route", "explain", "plan", "fill", "free", "wording", "wording_free", "blueprint", "build_script", "patch"):
        ids = chains.for_purpose(purpose)
        assert 1 <= len(ids) <= MAX_CHAIN and all(i.endswith(":free") for i in ids), purpose
    assert DEFAULT_PATH.exists()


def test_a_purpose_picks_its_chain_and_an_unknown_one_uses_the_default() -> None:
    chains = parse_chains(GOOD)
    assert chains.for_purpose("plan") == ("c/z:free",)
    assert chains.for_purpose("route") == ("a/x:free", "b/y:free")
    assert chains.for_purpose("something_new") == ("a/x:free", "b/y:free")
    assert chains.first() == "a/x:free"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: d["chains"].update(fast=["anthropic/claude-sonnet-5-5"]), "ending in \":free\""),
        (lambda d: d["chains"].update(fast=["a/x:free", "b/y"]), "ending in \":free\""),
        (lambda d: d["chains"].update(fast=[]), "1 to"),
        (lambda d: d["chains"].update(fast=[f"m{i}:free" for i in range(MAX_CHAIN + 1)]), "1 to"),
        (lambda d: d["chains"].update(fast=["a/x:free", "a/x:free"]), "twice"),
        (lambda d: d["purposes"].update(plan="nope"), "unknown chain"),
        (lambda d: d.update(default="nope"), '"default"'),
        (lambda d: d.update(chains={}), "non-empty"),
        (lambda d: d.pop("purposes"), '"purposes"'),
        (lambda d: d["chains"].update(fast=[7]), "ending in"),
    ],
)
def test_a_bad_chains_file_is_refused_with_a_message_that_names_the_problem(change, message: str) -> None:  # noqa: ANN001
    data = json.loads(json.dumps(GOOD))
    change(data)
    with pytest.raises(ChainsError, match=message):
        parse_chains(data)


def test_a_file_that_is_missing_or_not_json_or_not_an_object_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ChainsError, match="cannot read"):
        load_chains(tmp_path / "nope.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ChainsError, match="not valid JSON"):
        load_chains(bad)
    bad.write_text("[]", encoding="utf-8")
    with pytest.raises(ChainsError, match="JSON object"):
        load_chains(bad)


def test_a_custom_file_replaces_the_shipped_one(tmp_path: Path) -> None:
    path = tmp_path / "chains.json"
    path.write_text(json.dumps(GOOD), encoding="utf-8")
    assert load_chains(path).first() == "a/x:free"
