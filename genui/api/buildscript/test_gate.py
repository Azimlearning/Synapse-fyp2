"""The gate's logic on a fake model: it builds, checks in a real browser, and judges the criteria. It does not evaluate any model (V5-D17); the live run is `eval/buildscript/gate.py`."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from api import kitmanifest
from api.buildscript.conftest import BLUEPRINTS, script_text
from api.buildscript.gate import Item, build_all, check_all, format_report, summarise
from api.buildscript.test_writer import FakeService
from eval.buildscript import gate as cli

BP = (BLUEPRINTS / "good_hookes_mars_series.json").read_text(encoding="utf-8")
SCRIPT = script_text("springs_series_planet")
QUESTIONS = [{"id": "q1", "question": "Hooke's law, but with two springs in series on Mars."}, {"id": "q2", "question": "Two springs again."}]


def test_a_gate_run_on_a_fake_model_builds_checks_and_judges(manifest: kitmanifest.Manifest, kit_dist: Path) -> None:
    service = FakeService([BP, BP], [SCRIPT, SCRIPT])
    items = asyncio.run(build_all(service, QUESTIONS, manifest))
    check_all(items, kit_dist=kit_dist)
    assert all(i.passed for i in items) and all(b["ok"] for i in items for b in i.behaviours) and len(items[0].behaviours) == 3
    s = summarise(items)
    assert s["criteria"]["scripts_passing"] == {"value": 2, "limit": 2, "of": 2, "met": True}
    assert s["criteria"]["median_writer_tokens_out"]["met"] is True and s["criteria"]["owner_judgement"]["met"] is None
    assert s["automatic_verdict"].startswith("GO") and s["cost_usd"] == 0.0
    text = format_report(s)
    assert "PASSED" in text and "pending" in text and "fake/free-model" in text


def test_a_run_where_most_scripts_fail_is_a_no_go(manifest: kitmanifest.Manifest, kit_dist: Path) -> None:
    broken = SCRIPT.replace("@@END\n", "")
    service = FakeService([BP, BP, BP], [SCRIPT, broken, broken, broken, broken])
    items = asyncio.run(build_all(service, [*QUESTIONS, {"id": "q3", "question": "x"}], manifest))
    check_all(items, kit_dist=kit_dist)
    s = summarise(items)
    assert [i.passed for i in items] == [True, False, False]
    assert s["criteria"]["scripts_passing"]["met"] is False and s["automatic_verdict"] == "NO-GO"
    assert "FAILED" in format_report(s) and "refused twice" in format_report(s)


def test_a_page_that_passes_every_check_but_breaks_its_blueprint_is_reported(manifest: kitmanifest.Manifest, kit_dist: Path) -> None:
    flat = SCRIPT.replace("x1 = weight / k1 [m]", "x1 = weight / 20 [m]")  # spring 1 no longer stretches less when it is stiffer
    items = asyncio.run(build_all(FakeService([BP], [flat]), QUESTIONS[:1], manifest))
    check_all(items, kit_dist=kit_dist)
    assert items[0].built is not None and items[0].built.ok, "the page is valid in itself"
    failed = [b for b in items[0].behaviours if not b["ok"]]
    assert failed and "stiffer" in failed[0]["text"]


def test_the_median_is_judged_not_the_mean() -> None:
    from api.buildscript.writer import Built, Call

    def item(tokens: int) -> Item:
        b = Built("q", ok=True)
        b.calls.append(Call("build_script", 1, "m", "p", 10, tokens, 5.0, 0.0, True))
        it = Item("i", "q", b)
        it.verified = True
        return it

    s = summarise([item(1000), item(1200), item(9000)])
    assert s["criteria"]["median_writer_tokens_out"]["value"] == 1200 and s["criteria"]["median_writer_tokens_out"]["met"] is True
    s = summarise([item(3000), item(3100), item(100)])
    assert s["criteria"]["median_writer_tokens_out"]["met"] is False and s["automatic_verdict"] == "NO-GO"


def test_a_time_miss_alone_is_reported_but_is_not_a_no_go_on_free_models() -> None:
    from api.buildscript.writer import Built, Call

    def item(seconds: float) -> Item:
        b = Built("q", ok=True)
        b.calls.append(Call("build_script", 1, "m", "p", 10, 1000, seconds, 0.0, True))
        it = Item("i", "q", b)
        it.verified = True
        return it

    s = summarise([item(60.0), item(70.0), item(80.0)])
    assert s["criteria"]["median_writer_seconds"]["met"] is False and s["time_criterion_missed_only"] is True
    assert s["automatic_verdict"].startswith("GO")


# ── the command line refuses what it must ───────────────────────────────────────────────────────────────────────────────────
def test_the_draft_question_set_is_pinned_but_not_approved_so_the_live_run_refuses_it() -> None:
    assert cli.PIN.is_file() and cli.digest(cli.SET) == cli.PIN.read_text(encoding="utf-8").strip()
    data = json.loads(cli.SET.read_text(encoding="utf-8"))
    assert data["approved"] is False and len(data["questions"]) == 3
    assert "approved" in str(cli.load_set())


def test_a_changed_set_fails_its_pin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    changed = tmp_path / "T-gate.json"
    changed.write_text(cli.SET.read_text(encoding="utf-8").replace("Moon", "Venus"), encoding="utf-8")
    monkeypatch.setattr(cli, "SET", changed)
    assert "pinned hash" in str(cli.load_set())


def test_an_approved_and_pinned_set_loads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ok = tmp_path / "T-gate.json"
    ok.write_text(cli.SET.read_text(encoding="utf-8").replace('"approved": false', '"approved": true'), encoding="utf-8")
    pin = tmp_path / "T-gate.sha256"
    pin.write_text(cli.digest(ok) + "\n", encoding="utf-8")
    monkeypatch.setattr(cli, "SET", ok)
    monkeypatch.setattr(cli, "PIN", pin)
    loaded = cli.load_set()
    assert isinstance(loaded, dict) and len(loaded["questions"]) == 3


def test_the_gate_forces_the_paid_fallback_off() -> None:
    text = (Path(cli.__file__)).read_text(encoding="utf-8")
    assert "allow_paid_fallback=False" in text
