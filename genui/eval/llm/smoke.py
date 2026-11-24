"""A live smoke test of the free model chain (V5-D22, V5-D17). Not part of the test suite: it makes real requests.

It reads the settings (and so the key) inside this process, forces the paid Anthropic fallback OFF so nothing can be spent, sends one short request for each of three
purposes (each uses its own chain), and prints the model that answered, the tokens, the time and the cost. It never prints a key. The ledger is a scratch file, so a smoke
run does not touch the project's real ledger.

    uv run python -m eval.llm.smoke
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import time
from pathlib import Path

from api.core.errors import ProviderUnavailable
from api.core.settings import Settings
from api.llm.factory import build_ledger, build_llm_service
from api.llm.types import LLMRequest

PROMPT = "In one plain sentence, why does a spring stretch when a weight hangs from it?"
PURPOSES = ("explain", "plan", "wording")  # the fast, build and reader chains
MAX_TOKENS = 1500  # free reasoning models spend part of this thinking; a small limit comes back empty


async def main() -> int:
    if not Path(".env").exists():
        print("No .env in this folder. Create it here (see refdocs/guides/env_setup.md) with OPENROUTER_API_KEY, then run again.")
        return 2
    scratch = Path(tempfile.mkdtemp(prefix="synapse-smoke-")) / "ledger.db"
    settings = Settings(_env_file=".env", synapse_llm_mode="live", allow_paid_fallback=False, ledger_path=scratch)  # type: ignore[call-arg]
    missing = settings.missing_for_mode()
    if missing:
        print("Not ready:", "; ".join(f"{name}: {why}" for name, why in missing))
        return 2
    service = build_llm_service(settings, build_ledger(settings))
    provider = service._providers[0]  # noqa: SLF001
    print(f"provider: {provider.name}; paid fallback built: {len(service._providers) > 1}")  # noqa: SLF001
    failures = 0
    for purpose in PURPOSES:
        started = time.monotonic()
        try:
            result = await service.complete(LLMRequest(prompt=PROMPT, purpose=purpose, max_tokens=MAX_TOKENS))
        except ProviderUnavailable as exc:
            failures += 1
            cause = exc.__cause__
            print(f"{purpose:9} FAILED after {time.monotonic() - started:5.1f}s: {cause if cause is not None else exc}")
            continue
        words = " ".join(result.text.split())[:110]
        print(
            f"{purpose:9} {result.model}  in {result.tokens_in} out {result.tokens_out}  {time.monotonic() - started:5.1f}s  "
            f"${result.cost_usd:.4f}  {result.provider}  | {words}"
        )
    remaining = getattr(provider, "free_requests_remaining", None)
    print(f"free requests left today (as counted): {remaining if remaining is not None else 'unknown'}")
    print("spent in total: $0.0000 (the paid provider was not built)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
