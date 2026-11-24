"""The prototype pipeline (Blueprint, then Build Script) with a scripted fake service: retries quote the checker, a double refusal stops, a provider failure is reported.

These are automated tests on a fake model (V5-D17): they prove the plumbing and the retry rules, and measure nothing about a real model.
"""

from __future__ import annotations

import asyncio
import json

from api import kitmanifest, prompts
from api.buildscript import prompt as bsprompt
from api.buildscript.conftest import BLUEPRINTS, script_text
from api.buildscript.writer import build
from api.core.errors import ProviderUnavailable
from api.llm.types import LLMRequest, LLMResult
from api.schema.generated import Blueprint

BLUEPRINT = (BLUEPRINTS / "good_hookes_mars_series.json").read_text(encoding="utf-8")
SCRIPT = script_text("springs_series_planet")
QUESTION = "Hooke's law, but two springs in series on Mars."


class FakeService:
    """Answers each stage from a list, in order, and keeps every request so a test can read what the model was told."""

    def __init__(self, blueprints: list[str | Exception], scripts: list[str | Exception]) -> None:
        self.queues = {"blueprint": list(blueprints), "build_script": list(scripts)}
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResult:
        self.requests.append(request)
        item = self.queues[request.purpose].pop(0)
        if isinstance(item, Exception):
            raise item
        return LLMResult(item, "fake", "fake/free-model", 100, 200, 0.0, False)


def run(service: FakeService, manifest: kitmanifest.Manifest):  # noqa: ANN201
    return asyncio.run(build(service, QUESTION, manifest))


def test_the_happy_path_builds_a_page_in_two_calls(manifest: kitmanifest.Manifest) -> None:
    service = FakeService([BLUEPRINT], [SCRIPT])
    built = run(service, manifest)
    assert built.ok and built.html and built.blueprint is not None and built.script is not None
    assert [c.stage for c in built.calls] == ["blueprint", "build_script"] and all(c.accepted for c in built.calls)
    assert built.tokens_out == 400 and built.cost_usd == 0.0 and built.calls[0].model == "fake/free-model"
    assert "<svg" in built.html


def test_a_fenced_blueprint_with_a_sentence_around_it_is_read(manifest: kitmanifest.Manifest) -> None:
    built = run(FakeService([f"Here is the plan:\n```json\n{BLUEPRINT}\n```\nHope it helps."], [SCRIPT]), manifest)
    assert built.ok


def test_a_refused_blueprint_is_retried_once_with_the_checkers_words(manifest: kitmanifest.Manifest) -> None:
    bad = json.loads(BLUEPRINT)
    bad["interactions"] = [i | {"gesture": "rotate"} for i in bad["interactions"]]  # BP-004: no drag or drop
    service = FakeService([json.dumps(bad), BLUEPRINT], [SCRIPT])
    built = run(service, manifest)
    assert built.ok and len(built.calls_for("blueprint")) == 2
    assert "BP-004" in service.requests[1].prompt and "Your previous Blueprint was refused" in service.requests[1].prompt
    assert built.calls_for("blueprint")[0].reasons and not built.calls_for("blueprint")[0].accepted


def test_a_blueprint_with_a_wrong_shape_is_refused_by_the_strict_model(manifest: kitmanifest.Manifest) -> None:
    bad = json.loads(BLUEPRINT) | {"surprise": 1}
    service = FakeService([json.dumps(bad), BLUEPRINT], [SCRIPT])
    built = run(service, manifest)
    assert built.ok and "BP-000" in service.requests[1].prompt


def test_a_blueprint_refused_twice_stops_before_the_writer(manifest: kitmanifest.Manifest) -> None:
    service = FakeService(["no json here", "still none"], [])
    built = run(service, manifest)
    assert not built.ok and "Blueprint was refused twice" in built.reason and built.blueprint is None
    assert [r.purpose for r in service.requests] == ["blueprint", "blueprint"]


def test_a_refused_script_is_retried_once_with_the_checkers_words(manifest: kitmanifest.Manifest) -> None:
    bad = SCRIPT.replace("x1 = weight / k1 [m]", "x1 = weight / k9 [m]")
    service = FakeService([BLUEPRINT], [bad, SCRIPT])
    built = run(service, manifest)
    assert built.ok and len(built.calls_for("build_script")) == 2
    retry = service.requests[-1].prompt
    assert "BS-004" in retry and "k9" in retry and "Your previous Build Script was refused" in retry


def test_a_script_refused_twice_is_reported_and_no_page_is_made(manifest: kitmanifest.Manifest) -> None:
    bad = SCRIPT.replace("@@END\n", "")
    built = run(FakeService([BLUEPRINT], [bad, bad]), manifest)
    assert not built.ok and built.html is None and "Build Script was refused twice" in built.reason and "cut off" in built.reason


def test_a_script_that_lists_parts_is_refused_in_this_build(manifest: kitmanifest.Manifest) -> None:
    parts = SCRIPT.replace("@@PARTS\nnone", '@@PARTS\ng = planetGravity {"planet": "$g_planet"}')
    built = run(FakeService([BLUEPRINT], [parts, SCRIPT]), manifest)
    assert built.ok and len(built.calls_for("build_script")) == 2


def test_a_provider_failure_is_reported_not_raised(manifest: kitmanifest.Manifest) -> None:
    exc = ProviderUnavailable("down")
    exc.__cause__ = RuntimeError("openrouter: HTTP 401 401")
    built = run(FakeService([exc], []), manifest)
    assert not built.ok and "HTTP 401" in built.reason and built.calls[0].accepted is False


# ── the requests ────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_the_blueprint_request_carries_the_rules_and_the_question() -> None:
    req = bsprompt.blueprint_request(QUESTION, offers="- massHanger")
    assert req.purpose == "blueprint" and req.system
    assert QUESTION in req.prompt and "- massHanger" in req.prompt and "expectedBehaviour" in req.system


def test_the_writer_request_carries_the_worked_example_the_blueprint_and_the_question() -> None:
    bp = Blueprint.model_validate(json.loads(BLUEPRINT))
    req = bsprompt.writer_request(QUESTION, bp, retry="FIX THIS")
    assert req.purpose == "build_script" and req.tier == "standard"
    system = req.system or ""
    assert bsprompt.example_text().strip() in system and "@@END" in system
    assert QUESTION in req.prompt and '"concept"' in req.prompt and "FIX THIS" in req.prompt
    assert "data-synapse-handle" in system and "host.set" in system


def test_the_writer_system_prompt_is_identical_for_two_questions_so_a_provider_can_cache_it() -> None:
    bp = Blueprint.model_validate(json.loads(BLUEPRINT))
    a = bsprompt.writer_request("one", bp)
    b = bsprompt.writer_request("two", bp, retry="x")
    assert a.system == b.system


def test_the_packs_stay_inside_their_budgets() -> None:
    bp = Blueprint.model_validate(json.loads(BLUEPRINT))
    for name, req in (("blueprint", bsprompt.blueprint_request(QUESTION)), ("build_script", bsprompt.writer_request(QUESTION, bp))):
        assert prompts.estimate_tokens(req.system or "") <= prompts.load(name).budget, name


def test_the_worked_example_in_the_prompt_is_a_reply_that_passes_every_check(manifest: kitmanifest.Manifest) -> None:
    from api.buildscript.validate import validate

    assert validate(bsprompt.example_text(), manifest, early_stop=False) == []


def test_extract_json_reports_why_there_is_none() -> None:
    assert bsprompt.extract_json("nothing") == "the reply has no JSON object"
    assert "not valid" in str(bsprompt.extract_json("{ nope }"))
    assert bsprompt.extract_json('["a"] {"a": 1}') == {"a": 1}


def test_no_pack_in_the_prototype_uses_a_long_dash() -> None:
    for name in ("blueprint", "build_script"):
        text = (prompts.DIR / f"{name}.v1.md").read_text(encoding="utf-8")
        assert "—" not in text and "–" not in text, name
