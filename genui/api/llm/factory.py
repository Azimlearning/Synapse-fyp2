# Adapted from Azimlearning/Arcana-v2, api/llm/factory.py @ 21c6dcf5. Read in full. v4 change: live mode built only the Anthropic provider, after the key,
# the cap and an absolute ledger path were present. v5 change (V5-D22): free OpenRouter models first, Anthropic last and only while the paid fallback is allowed.
"""Build the LLM service for the configured mode (SYNAPSE_LLM_MODE)."""

from __future__ import annotations

from collections.abc import Callable

from api.core.errors import ProviderUnavailable
from api.core.settings import ConfigError, Settings
from api.llm.chains import ChainsError, load_chains
from api.llm.ledger import SpendLedger, engine_for
from api.llm.providers.anthropic import AnthropicProvider
from api.llm.providers.base import Provider
from api.llm.providers.fake import FakeProvider
from api.llm.providers.openrouter import OpenRouterProvider
from api.llm.service import LLMService
from api.llm.types import LLMRequest


def _require_live_prerequisites(settings: Settings) -> None:
    """Live mode never runs uncapped, whatever path built the Settings (load_settings checks too, but Settings can be constructed directly)."""
    missing = settings.missing_for_mode()
    if missing:
        raise ConfigError(missing)


def build_ledger(settings: Settings) -> SpendLedger:
    """The ledger at the configured path, capped by LLM_MONTHLY_CAP_USD. No cap means nothing paid can be spent: fake mode, or live mode with only free models."""
    _require_live_prerequisites(settings)
    return SpendLedger(
        engine_for(settings.resolved_ledger_path()), settings.llm_monthly_cap_usd, total_cap_usd=settings.llm_total_cap_usd
    )


def build_llm_service(
    settings: Settings,
    ledger: SpendLedger,
    fake_responder: Callable[[LLMRequest], str] | None = None,
) -> LLMService:
    """Fake mode: one free fake provider. Live mode (V5-D22): free OpenRouter models first, in chains per purpose, then the paid Anthropic key, which is built only
    while ALLOW_PAID_FALLBACK is true and is then behind the ledger and its cap. Either key alone works; with neither, live mode refuses to start."""
    if settings.synapse_llm_mode == "fake":
        if fake_responder is None:
            from api.pipeline.fakes import (
                fake_responder as pipeline_fakes,
            )  # purpose-aware fakes for the pipeline (route, plan, fill)

            fake_responder = pipeline_fakes
        provider = FakeProvider(fake_responder)
        return LLMService(provider, None, ledger, prompt_caching=settings.prompt_caching)
    _require_live_prerequisites(settings)
    providers: list[Provider] = []
    if settings.openrouter_api_key is not None and settings.openrouter_api_key.get_secret_value().strip():
        try:
            chains = load_chains(settings.model_chains_path)
        except ChainsError as exc:
            raise ConfigError([("MODEL_CHAINS_PATH", str(exc))]) from exc
        providers.append(
            OpenRouterProvider(
                settings.openrouter_api_key.get_secret_value(), chains, allow_training=settings.openrouter_allow_training_providers
            )
        )
    openrouter_key = settings.openrouter_api_key.get_secret_value().strip() if settings.openrouter_api_key is not None else ""
    if settings.allow_paid_fallback and settings.openrouter_paid_chains_path is not None and openrouter_key:
        # V5-D26: Claude through OpenRouter credits as the paid provider, behind the same ledger and cap as the Anthropic key.
        try:
            paid_chains = load_chains(settings.openrouter_paid_chains_path)
        except ChainsError as exc:
            raise ConfigError([("OPENROUTER_PAID_CHAINS_PATH", str(exc))]) from exc
        if not paid_chains.paid:
            raise ConfigError([("OPENROUTER_PAID_CHAINS_PATH", 'the file must say "paid": true')])
        providers.append(OpenRouterProvider(openrouter_key, paid_chains))
    elif settings.allow_paid_fallback and settings.anthropic_api_key is not None and settings.anthropic_api_key.get_secret_value().strip():
        providers.append(AnthropicProvider(settings.anthropic_api_key.get_secret_value()))
    if not providers:
        raise ProviderUnavailable("Live mode needs OPENROUTER_API_KEY, or ANTHROPIC_API_KEY with ALLOW_PAID_FALLBACK on; no provider was built.")
    first = frozenset(p.strip() for p in settings.paid_first_purposes.split(",") if p.strip())
    return LLMService(
        providers[0], providers[1] if len(providers) > 1 else None, ledger, prompt_caching=settings.prompt_caching, fallback_first=first
    )
