"""V5-D26: a paid chains file (Claude through OpenRouter credits) and paid-first purposes. The paid provider is built only behind the cap, a paid call is reserved
against the model its purpose uses plus the provider's output allowance, the free provider is still tried when the paid one fails, and nothing touches the network."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

from api.core.settings import ConfigError, load_settings
from api.llm.chains import DEFAULT_PATH, ChainsError, load_chains, parse_chains
from api.llm.factory import build_ledger, build_llm_service
from api.llm.ledger import SpendLedger, engine_for
from api.llm.pricing import estimate_call_cost
from api.llm.providers.base import ProviderFailure
from api.llm.providers.openrouter import PAID_REASONING_ALLOWANCE, OpenRouterProvider
from api.llm.service import LLMService
from api.llm.types import LLMRequest, ProviderResponse, Tier

PAID_FILE = DEFAULT_PATH.with_name("chains-paid.json")
PAID = {"paid": True, "chains": {"light": ["anthropic/claude-haiku-5.5"], "writer": ["anthropic/claude-sonnet-5.5"]}, "purposes": {"free": "writer"}, "default": "light"}


def test_the_shipped_paid_file_loads_and_is_marked_paid() -> None:
    chains = load_chains(PAID_FILE)
    assert chains.paid
    assert chains.model_for_purpose("free") == "anthropic/claude-sonnet-5.5"
    assert chains.model_for_purpose("plan") == "anthropic/claude-haiku-5.5"


def test_a_free_file_still_refuses_a_paid_id() -> None:
    data = {"chains": {"fast": ["anthropic/claude-haiku-5.5"]}, "purposes": {}, "default": "fast"}
    with pytest.raises(ChainsError, match="ending in"):
        parse_chains(data)


def test_a_paid_file_refuses_a_free_id_and_a_non_boolean_flag() -> None:
    with pytest.raises(ChainsError, match="paid ids only"):
        parse_chains({**PAID, "chains": {"light": ["nvidia/x:free"]}, "purposes": {}})
    with pytest.raises(ChainsError, match='"paid"'):
        parse_chains({**PAID, "paid": "yes"})


def test_the_paid_provider_reserves_by_purpose_and_adds_its_allowance() -> None:
    provider = OpenRouterProvider("sk-or-test", parse_chains(PAID))
    request = LLMRequest(prompt="x", purpose="free", max_tokens=100)
    assert provider.paid and provider.model_for_request(request) == "anthropic/claude-sonnet-5.5"
    assert provider.output_allowance == PAID_REASONING_ALLOWANCE
    body = provider._body(request, ["anthropic/claude-sonnet-5.5"], stream=False)  # noqa: SLF001
    assert body["max_tokens"] == 100 + PAID_REASONING_ALLOWANCE
    assert "provider" not in body and "reasoning" not in body


@dataclass
class Scripted:
    """A provider that answers or fails as told and remembers what it was asked."""

    name: str
    model: str
    fail: bool = False
    output_allowance: int = 0
    asked: list[str] = field(default_factory=list)

    def model_for(self, tier: Tier) -> str:  # noqa: ARG002
        return self.model

    async def complete(self, request: LLMRequest, model: str, on_text=None) -> ProviderResponse:  # noqa: ANN001, ARG002
        self.asked.append(request.purpose)
        if self.fail:
            raise ProviderFailure(self.name, "HTTP 429", "transient")
        return ProviderResponse(text="ok", model=model, tokens_in=10, tokens_out=10, cost_usd=None)


def _ledger(tmp_path: Path, cap: float | None) -> SpendLedger:
    return SpendLedger(engine_for(tmp_path / "ledger.db"), cap, clock=lambda: datetime(2026, 11, 24, tzinfo=UTC))


async def test_a_paid_first_purpose_goes_to_the_paid_provider_and_others_stay_free_first(tmp_path: Path) -> None:
    free = Scripted("openrouter", "nvidia/x:free")
    paid = Scripted("openrouter", "anthropic/claude-haiku-5.5")
    service = LLMService(free, paid, _ledger(tmp_path, 5.0), fallback_first=frozenset({"plan"}))
    await service.complete(LLMRequest(prompt="q", purpose="plan"))
    await service.complete(LLMRequest(prompt="q", purpose="route"))
    assert paid.asked == ["plan"] and free.asked == ["route"]


async def test_when_the_paid_provider_fails_the_free_one_still_answers(tmp_path: Path) -> None:
    free = Scripted("openrouter", "nvidia/x:free")
    paid = Scripted("openrouter", "anthropic/claude-haiku-5.5", fail=True)
    service = LLMService(free, paid, _ledger(tmp_path, 5.0), fallback_first=frozenset({"plan"}))
    result = await service.complete(LLMRequest(prompt="q", purpose="plan"))
    assert result.text == "ok" and paid.asked == ["plan"] and free.asked == ["plan"]


async def test_the_cap_counts_the_allowance_and_refuses_before_sending(tmp_path: Path) -> None:
    from api.core.errors import SpendCapExceeded

    paid = Scripted("openrouter", "anthropic/claude-sonnet-5.5", output_allowance=4096)
    request = LLMRequest(prompt="q", purpose="free", max_tokens=100)
    with_allowance = estimate_call_cost("openrouter", paid.model, LLMRequest(prompt="q", purpose="free", max_tokens=4196))
    without = estimate_call_cost("openrouter", paid.model, request)
    cap = (with_allowance + without) / 2  # covers the bare request, not the allowance
    service = LLMService(paid, None, _ledger(tmp_path, cap))
    with pytest.raises(SpendCapExceeded):
        await service.complete(request)
    assert paid.asked == []


@pytest.mark.usefixtures("clean_env")
def test_the_factory_builds_the_paid_openrouter_provider_only_behind_a_cap(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    paid_file = tmp_path / "paid.json"
    paid_file.write_text(json.dumps(PAID), encoding="utf-8")
    monkeypatch.setenv("SYNAPSE_LLM_MODE", "live")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-not-real")
    monkeypatch.setenv("OPENROUTER_PAID_CHAINS_PATH", str(paid_file))
    monkeypatch.setenv("LEDGER_PATH", str(tmp_path / "ledger.db"))
    monkeypatch.setenv("PAID_FIRST_PURPOSES", "plan, free")
    with pytest.raises(ConfigError, match="LLM_MONTHLY_CAP_USD"):
        load_settings(env_file=None)
    monkeypatch.setenv("LLM_MONTHLY_CAP_USD", "3")
    settings = load_settings(env_file=None)
    service = build_llm_service(settings, build_ledger(settings))
    providers = service._providers  # noqa: SLF001
    assert len(providers) == 2 and not providers[0].paid and providers[1].paid  # type: ignore[attr-defined]
    assert service._fallback_first == frozenset({"plan", "free"})  # noqa: SLF001
    monkeypatch.setenv("ALLOW_PAID_FALLBACK", "false")
    settings = load_settings(env_file=None)
    assert len(build_llm_service(settings, build_ledger(settings))._providers) == 1  # noqa: SLF001
