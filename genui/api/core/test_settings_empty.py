"""A blank line in `.env` (a template with the values left out) means the setting is unset, not an empty string that cannot be parsed."""

from __future__ import annotations

from pathlib import Path

from api.core.settings import Settings


def test_blank_values_in_the_env_file_mean_unset(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("LLM_MONTHLY_CAP_USD=\nLLM_TOTAL_CAP_USD=\nANTHROPIC_API_KEY=\nCORPUS_DIR=\nSYNAPSE_LLM_MODE=fake\n", encoding="utf-8")
    settings = Settings(_env_file=env)  # type: ignore[call-arg]
    assert settings.llm_monthly_cap_usd is None and settings.llm_total_cap_usd is None
    assert settings.anthropic_api_key is None and settings.corpus_dir is None and settings.synapse_llm_mode == "fake"
