"""The V5-2 prototype pipeline: question to Blueprint to Build Script to page (build-script.md, blueprint.md).

    Blueprint (one call, one retry) -> BP checks -> Build Script (one call, one retry) -> validate -> assemble

It is a prototype beside the pipeline, not in it: `api/pipeline/run.py` is untouched until V5-3. Each call is booked by the service and its ledger like any other, and a
free model costs $0 there. What is recorded for every call (model that answered, tokens, seconds, what the checker said) is what the live gate reports.

Not done here, on purpose: the reply is checked once it has arrived whole, not unit by unit as it streams (the units are ready, V5-3 streams), and Kit parts are not
mounted, so the Build Script's PARTS are always `none`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol

from pydantic import ValidationError

from api.blueprint.checks import Finding, check
from api.buildscript import prompt
from api.buildscript.assemble import AssembleError, assemble
from api.buildscript.model import BuildScript
from api.buildscript.parse import parse
from api.buildscript.validate import validate
from api.core.errors import ProviderUnavailable
from api.kitmanifest import Manifest
from api.llm.types import LLMRequest, LLMResult
from api.schema.generated import Blueprint

MAX_ATTEMPTS = 2
"""The first reply and one retry with the checker's reasons (V5-D02)."""


class Service(Protocol):
    async def complete(self, request: LLMRequest) -> LLMResult: ...


@dataclass
class Call:
    stage: str  # blueprint | build_script
    attempt: int
    model: str
    provider: str
    tokens_in: int
    tokens_out: int
    seconds: float
    cost_usd: float
    accepted: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class Built:
    question: str
    ok: bool = False
    reason: str = ""
    blueprint: Blueprint | None = None
    script: BuildScript | None = None
    html: str | None = None
    raw_script: str = ""
    calls: list[Call] = field(default_factory=list)

    def calls_for(self, stage: str) -> list[Call]:
        return [c for c in self.calls if c.stage == stage]

    @property
    def tokens_out(self) -> int:
        return sum(c.tokens_out for c in self.calls)

    @property
    def cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.calls)


async def _ask(service: Service, request: LLMRequest, built: Built, stage: str, attempt: int) -> str | None:
    started = time.monotonic()
    try:
        result = await service.complete(request)
    except ProviderUnavailable as exc:
        cause = exc.__cause__
        built.reason = f"the {stage} call failed: {cause if cause is not None else exc}"
        built.calls.append(Call(stage, attempt, "", "", 0, 0, time.monotonic() - started, 0.0, False, [built.reason]))
        return None
    built.calls.append(
        Call(stage, attempt, result.model, result.provider, result.tokens_in, result.tokens_out, time.monotonic() - started, result.cost_usd, False)
    )
    return result.text


async def make_blueprint(service: Service, question: str, manifest: Manifest, stored_ids: frozenset[str], built: Built) -> bool:
    retry = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        text = await _ask(service, prompt.blueprint_request(question, retry=retry), built, "blueprint", attempt)
        if text is None:
            return False
        data = prompt.extract_json(text)
        findings: list[Finding] = []
        if isinstance(data, str):
            findings = [Finding("BP-000", "reply", data, "Reply with one JSON object and nothing else.")]
        else:
            try:
                blueprint = Blueprint.model_validate(data)
            except ValidationError as exc:
                findings = [Finding("BP-000", ".".join(str(p) for p in err["loc"]) or "reply", err["msg"], "Use exactly the fields and kinds the pack lists.") for err in exc.errors()[:6]]
            else:
                findings = check(blueprint, manifest, stored_ids)
                if not findings:
                    built.blueprint = blueprint
                    built.calls[-1].accepted = True
                    return True
        built.calls[-1].reasons = [str(f) for f in findings]
        retry = prompt.retry_text(findings, "Blueprint")
    built.reason = "the Blueprint was refused twice: " + "; ".join(built.calls[-1].reasons[:3])
    return False


async def write_script(service: Service, question: str, blueprint: Blueprint, manifest: Manifest, built: Built) -> bool:
    retry = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        text = await _ask(service, prompt.writer_request(question, blueprint, retry=retry), built, "build_script", attempt)
        if text is None:
            return False
        built.raw_script = text
        findings = validate(text, manifest)
        if not findings:
            parsed = parse(text)
            if isinstance(parsed, str):  # cannot happen after validate, which parses first; kept so a future change cannot slip a string through
                findings = [Finding("BS-000", "reply", parsed, "Reply in the labelled sections.")]
            else:
                try:
                    built.html = assemble(parsed)
                except AssembleError as exc:
                    findings = [Finding("BS-008", "reply", str(exc), "Write @@PARTS as none.")]
                else:
                    built.script = parsed
                    built.calls[-1].accepted = True
                    return True
        built.calls[-1].reasons = [str(f) for f in findings]
        retry = prompt.retry_text(findings, "Build Script")
    built.reason = "the Build Script was refused twice: " + "; ".join(built.calls[-1].reasons[:3])
    return False


async def build(service: Service, question: str, manifest: Manifest, stored_ids: frozenset[str] = frozenset()) -> Built:
    """Question to page. `ok` is True only when a Blueprint passed its checks and a Build Script passed validation and assembled; whether the page survives the real
    browser (the existing Free checks, the Blueprint's behaviours) is the caller's next step."""
    built = Built(question)
    if not await make_blueprint(service, question, manifest, stored_ids, built) or built.blueprint is None:
        return built
    if await write_script(service, question, built.blueprint, manifest, built):
        built.ok = True
    return built
