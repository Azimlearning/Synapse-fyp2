"""V5-D22 wiring: live mode builds OpenRouter first and Anthropic last, either key alone is enough, and the paid fallback can be switched off."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from api.core.settings import ConfigError, Settings
from api.llm.factory import build_ledger, build_llm_service
from api.llm.ledger import SpendLedger, engine_for
from api.llm.providers.anthropic import AnthropicProvider
from api.llm.providers.openrouter import OpenRouterProvider
from api.llm.service import LLMService
from api.llm.types import LLMRequest

pytestmark = pytest.mark.usefixtures("clean_env")  # no real key or setting from the developer's environment can reach these tests


def live(tmp_path: Path, **kw: object) -> Settings:
    return Settings.model_validate({"synapse_llm_mode": "live", "ledger_path": str(tmp_path / "ledger.db"), **kw})


def test_a_free_key_alone_is_enough_and_needs_no_cap(tmp_path: Path) -> None:
    settings = live(tmp_path, openrouter_api_key="sk-or-x")
    assert settings.missing_for_mode() == []
    ledger = build_ledger(settings)
    assert ledger.remaining_usd() is None, "nothing paid can be spent, so there is no cap to enforce"
    (provider,) = build_llm_service(settings, ledger)._providers  # noqa: SLF001
    assert isinstance(provider, OpenRouterProvider)


def test_both_keys_build_the_free_provider_first_and_the_paid_one_last_behind_a_cap(tmp_path: Path) -> None:
    settings = live(tmp_path, openrouter_api_key="sk-or-x", anthropic_api_key="sk-ant-x", llm_monthly_cap_usd=5)
    ledger = build_ledger(settings)
    providers = build_llm_service(settings, ledger)._providers  # noqa: SLF001
    assert [p.name for p in providers] == ["openrouter", "anthropic"] and isinstance(providers[1], AnthropicProvider)
    assert ledger.remaining_usd() == 5.0


def test_both_keys_without_a_cap_are_refused_because_the_paid_provider_would_be_uncapped(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="LLM_MONTHLY_CAP_USD"):
        build_ledger(live(tmp_path, openrouter_api_key="sk-or-x", anthropic_api_key="sk-ant-x"))


def test_switching_the_paid_fallback_off_builds_only_the_free_provider_and_needs_no_cap(tmp_path: Path) -> None:
    settings = live(tmp_path, openrouter_api_key="sk-or-x", anthropic_api_key="sk-ant-x", allow_paid_fallback=False)
    assert settings.missing_for_mode() == []
    providers = build_llm_service(settings, build_ledger(settings))._providers  # noqa: SLF001
    assert [p.name for p in providers] == ["openrouter"]


def test_a_paid_key_that_is_switched_off_is_not_a_provider(tmp_path: Path) -> None:
    settings = live(tmp_path, anthropic_api_key="sk-ant-x", allow_paid_fallback=False)
    with pytest.raises(ConfigError) as err:
        build_ledger(settings)
    assert "OPENROUTER_API_KEY" in str(err.value) and "ALLOW_PAID_FALLBACK" in str(err.value)


def test_the_anthropic_key_alone_still_works_as_in_v4(tmp_path: Path) -> None:
    settings = live(tmp_path, anthropic_api_key="sk-ant-x", llm_monthly_cap_usd=5)
    (provider,) = build_llm_service(settings, build_ledger(settings))._providers  # noqa: SLF001
    assert isinstance(provider, AnthropicProvider)


def test_neither_key_is_refused_naming_both(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as err:
        build_ledger(live(tmp_path))
    assert "OPENROUTER_API_KEY" in str(err.value) and "ANTHROPIC_API_KEY" in str(err.value)


def test_a_broken_chains_file_stops_the_build_naming_the_setting(tmp_path: Path) -> None:
    path = tmp_path / "chains.json"
    path.write_text(json.dumps({"chains": {"fast": ["anthropic/claude-sonnet-5-5"]}, "purposes": {}, "default": "fast"}), encoding="utf-8")
    settings = live(tmp_path, openrouter_api_key="sk-or-x", model_chains_path=str(path))
    with pytest.raises(ConfigError) as err:
        build_llm_service(settings, build_ledger(settings))
    assert "MODEL_CHAINS_PATH" in str(err.value) and ":free" in str(err.value)


def test_the_training_providers_setting_reaches_the_provider(tmp_path: Path) -> None:
    settings = live(tmp_path, openrouter_api_key="sk-or-x", openrouter_allow_training_providers=False)
    (provider,) = build_llm_service(settings, build_ledger(settings))._providers  # noqa: SLF001
    assert isinstance(provider, OpenRouterProvider) and provider._allow_training is False  # noqa: SLF001


# ── through the service: free first, paid last, each booked at its own price ───────────────────────────────────────────────


def _service(tmp_path: Path, openrouter, anthropic, cap: float = 5.0) -> tuple[LLMService, SpendLedger]:  # noqa: ANN001
    from api.llm.chains import load_chains

    ledger = SpendLedger(engine_for(tmp_path / "l.db"), cap, clock=lambda: datetime(2026, 11, 14, tzinfo=UTC))
    free = OpenRouterProvider("sk-or-x", load_chains(), client=httpx.AsyncClient(transport=httpx.MockTransport(openrouter)))
    free._quota_known = True  # noqa: SLF001
    paid = AnthropicProvider("sk-ant-x", client=httpx.AsyncClient(transport=httpx.MockTransport(anthropic)))
    return LLMService(free, paid, ledger), ledger


def _openrouter_ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "nvidia/nemotron-3.5-lightning:free",
            "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "free answer"}}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 500, "cost": 0},
        },
    )


def _anthropic_ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "claude-sonnet-5-5",
            "content": [{"type": "text", "text": "paid answer"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 1000, "output_tokens": 500},
        },
    )


async def test_a_free_answer_costs_nothing_and_records_the_model_that_wrote_it(tmp_path: Path) -> None:
    service, ledger = _service(tmp_path, _openrouter_ok, _anthropic_ok)
    result = await service.complete(LLMRequest(prompt="why", purpose="explain", max_tokens=100))
    assert (result.provider, result.text, result.cost_usd, result.fell_back) == ("openrouter", "free answer", 0.0, False)
    assert result.model == "nvidia/nemotron-3.5-lightning:free"
    assert ledger.remaining_usd() == 5.0


async def test_when_every_free_model_fails_the_paid_key_answers_and_only_it_is_booked(tmp_path: Path) -> None:
    def down(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"code": 429, "message": "rate limited"}})

    service, ledger = _service(tmp_path, down, _anthropic_ok)
    result = await service.complete(LLMRequest(prompt="why", purpose="explain", max_tokens=100))
    assert (result.provider, result.text, result.fell_back) == ("anthropic", "paid answer", True)
    assert result.cost_usd == pytest.approx((1000 * 2.0 + 500 * 10.0) / 1_000_000)
    assert ledger.remaining_usd() == pytest.approx(5.0 - result.cost_usd)


async def test_a_bad_free_key_does_not_stop_the_run_the_paid_key_still_answers(tmp_path: Path) -> None:
    def unauthorised(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"code": 401, "message": "no"}})

    service, _ = _service(tmp_path, unauthorised, _anthropic_ok)
    result = await service.complete(LLMRequest(prompt="why", purpose="explain", max_tokens=100))
    assert result.provider == "anthropic"
