"""The requests for the two model calls of the V5-2 prototype: the Blueprint planner and the Build Script writer.

Both read their text from prompt packs (`api/prompts/blueprint.v1.md`, `api/prompts/build_script.v1.md`); nothing here is prompt text except the retry note, which
quotes the checker's own words. The writer's pack carries one complete worked reply, taken from a fixture that passes every check, so the example can never drift from
the rules it shows.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from api import prompts
from api.blueprint.checks import Finding
from api.llm.types import LLMRequest
from api.schema.generated import Blueprint

FIXTURES = Path(__file__).parent / "fixtures"
EXAMPLE = "springs_series_planet"
"""The fixture shown to the writer as the worked reply. It has a drop, three drags, formulas with units and a drawing that fills the bench."""
MAX_RETRY_FINDINGS = 6
BLUEPRINT_MAX_TOKENS = 8000
WRITER_MAX_TOKENS = 14000
"""Free reasoning models spend part of the limit thinking, and a small limit comes back empty (docs/model-chain.md); the ledger books free models at $0."""


@cache
def example_text() -> str:
    return (FIXTURES / f"{EXAMPLE}.txt").read_text(encoding="utf-8").strip() + "\n"


def retry_text(findings: list[Finding], what: str) -> str:
    """The note that goes back to the model after a refusal, in the checker's words. Empty when there is nothing to fix."""
    if not findings:
        return ""
    lines = [f"- {f.rule} at {f.path}: {f.reason} {f.fix}" for f in findings[:MAX_RETRY_FINDINGS]]
    more = f"\n(and {len(findings) - MAX_RETRY_FINDINGS} more)" if len(findings) > MAX_RETRY_FINDINGS else ""
    return f"Your previous {what} was refused for these reasons. Fix exactly these and write the whole {what} again:\n" + "\n".join(lines) + more


def blueprint_request(question: str, offers: str = "none", retry: str = "") -> LLMRequest:
    system, user = prompts.load("blueprint").render_parts(question=question.strip(), offers=offers.strip() or "none")
    return LLMRequest(
        prompt=(user + ("\n" + retry if retry else "")).strip(),
        system=system.strip(),
        purpose="blueprint",
        tier="light",
        max_tokens=BLUEPRINT_MAX_TOKENS,
    )


def writer_request(question: str, blueprint: Blueprint, retry: str = "") -> LLMRequest:
    system, user = prompts.load("build_script").render_parts(
        example=example_text(),
        question=question.strip(),
        blueprint=json.dumps(blueprint.model_dump(mode="json"), indent=1),
        retry=retry,
    )
    return LLMRequest(prompt=user.strip(), system=system.strip(), purpose="build_script", tier="standard", max_tokens=WRITER_MAX_TOKENS)


def extract_json(text: str) -> dict | str:
    """The JSON object in a model's reply (a code fence or a sentence around it is tolerated), or the reason there is none."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return "the reply has no JSON object"
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        return f"the JSON is not valid ({exc.msg} at character {exc.pos})"
    return data if isinstance(data, dict) else "the reply is JSON but not an object"
