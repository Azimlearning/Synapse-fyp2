"""The speed report: nested layers are summed once, paths are grouped, percentiles are nearest-rank, and the CLI refuses a missing file."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.speed import report


def trace(outcome: str, layers: list[tuple[str, int]], cost: float = 0.0) -> dict:
    records = [{"layer": name, "ms": ms, "status": "ok", "detail": {"cost_usd": cost} if name.startswith("llm:") else {}} for name, ms in layers]
    return {"outcome": outcome, "records": records, "llm_calls": sum(1 for n, _ in layers if n.startswith("llm:")), "question_sha256": "x", "request_id": "r"}


COMPOSE = trace("compose", [("intake", 0), ("llm:route", 1785), ("route", 2105), ("llm:explain", 3034), ("explain", 3035), ("llm:plan", 3609), ("plan_checks", 3614), ("verify", 12293), ("deliver", 16)], 0.01)


def test_a_request_s_time_is_its_layers_not_its_layers_plus_the_model_calls_inside_them() -> None:
    assert report.layer_ms(COMPOSE) == 0 + 2105 + 3035 + 3614 + 12293 + 16
    assert report.model_ms(COMPOSE) == 1785 + 3034 + 3609
    assert report.cost_usd(COMPOSE) == pytest.approx(0.03)


def test_paths_group_the_outcomes() -> None:
    names = {o: report.path_of({"outcome": o}) for o in ("library:instantiate", "library:free", "compose", "instantiate", "free", "text_only", "error", "unknown", "weird")}
    assert names["library:instantiate"] == names["library:free"] == "library"
    assert names["compose"] == names["instantiate"] == "compose"
    assert names["free"] == "free" and names["text_only"] == "text only" and names["error"] == "error"
    assert names["unknown"] == names["weird"] == "other"


def test_percentiles_are_nearest_rank_values_that_occurred() -> None:
    xs = [1.0, 2.0, 3.0, 4.0, 10.0]
    assert report.percentile(xs, 50) == 3.0 and report.percentile(xs, 90) == 10.0 and report.percentile(xs, 100) == 10.0
    assert report.percentile([7.0], 90) == 7.0


def test_the_summary_has_one_row_per_path_with_median_p90_and_cost() -> None:
    hit = trace("library:instantiate", [("intake", 0), ("lookup", 20)])
    s = report.summarise([hit, hit, COMPOSE])
    assert s["library"]["n"] == 2 and s["library"]["median_s"] == 0.02 and s["library"]["cost_mean_usd"] == 0.0
    assert s["compose"]["n"] == 1 and s["compose"]["median_s"] == 21.06 and s["compose"]["cost_total_usd"] == 0.03 and s["compose"]["llm_calls_mean"] == 3.0


def test_the_table_lists_the_paths_in_a_fixed_order() -> None:
    text = report.format_table(report.summarise([COMPOSE, trace("library:free", [("lookup", 5)])]), 2, "x")
    assert text.index("| library |") < text.index("| compose |") and "2 requests from x" in text


def test_the_command_line_reads_a_file_and_refuses_a_missing_or_empty_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    f = tmp_path / "traces.jsonl"
    f.write_text(json.dumps(COMPOSE) + "\n\n" + json.dumps(COMPOSE) + "\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["report", "--traces", str(f)])
    assert report.main() == 0 and "compose" in capsys.readouterr().out
    monkeypatch.setattr("sys.argv", ["report", "--traces", str(f), "--since", "5"])
    assert report.main() == 2
    monkeypatch.setattr("sys.argv", ["report", "--traces", str(tmp_path / "none.jsonl")])
    assert report.main() == 2


def test_the_v4_baseline_reproduces_where_the_v4_trace_file_is_present() -> None:
    """The first 128 lines are what STATUS.md's baseline was taken from: compose about 24 s, free model time inside 175 to 429 s."""
    path = Path(__file__).resolve().parents[3] / "Synapse-V4" / "data" / "traces.jsonl"
    if not path.is_file():
        pytest.skip("the v4 trace file is not on this machine")
    s = report.summarise(report.load(path)[:128])
    assert 20 <= s["compose"]["median_s"] <= 30
    assert 175 <= s["free"]["model_median_s"] <= 429
