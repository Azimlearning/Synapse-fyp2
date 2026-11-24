"""Model ids per provider and tier (D-08: heavy, standard, light).

Anthropic ids are from the current model table (2026-09). OpenRouter ids are ASSUMED to follow its
dotted naming ("anthropic/claude-sonnet-5.5"); its public model list did not show the sonnet and
haiku entries when checked on 2026-10-05, so task 10's live run is where these get confirmed.
"""

from __future__ import annotations

from api.llm.types import Tier

ANTHROPIC_MODELS: dict[Tier, str] = {
    "heavy": "claude-opus-5-5",
    "standard": "claude-sonnet-5-5",
    "light": "claude-haiku-4-5",
}

# Routing (2026-11-23): 1. Anthropic direct (the primary, above); 2. if it fails, the same Claude tier through OpenRouter; 3. if
# that fails too, OpenRouter's FREE models, tried in order inside the same request (OpenRouter's `models` routing). Free ids end in
# ":free", so OpenRouter never bills them; each answered live on 2026-11-23. A free reasoning model (nemotron-3-ultra) is left out:
# it spent the token budget thinking and returned truncated JSON on a writing task.
OPENROUTER_MODELS: dict[Tier, str] = {
    "heavy": "anthropic/claude-opus-5.5",
    "standard": "anthropic/claude-sonnet-5.5",
    "light": "anthropic/claude-haiku-4.5",
}

OPENROUTER_FREE_FALLBACKS: tuple[str, ...] = (
    "google/gemma-4-31b-it:free",
    "thinkingmachines/inkling-2-small:free",
)
