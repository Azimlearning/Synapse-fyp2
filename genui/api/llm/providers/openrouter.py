"""The OpenRouter provider: free models first (V5-D22, docs/model-chain.md).

Read against OpenRouter's current docs on 2026-11-14: chat completions (`POST /api/v1/chat/completions`, `messages`, `models`, `provider`, `max_tokens`,
`reasoning`), streaming (server-sent events, `data:` lines, `: OPENROUTER PROCESSING` comment lines to ignore, `[DONE]`, usage in the last chunk, an error that
arrives after streaming started is a chunk with an `error`), errors (a JSON `{"error": {"code", "message", "metadata"}}` and the status codes 400, 401, 402, 403,
408, 429, 502, 503), model fallbacks (`models` is tried in order and fails over on errors, rate limits, downtime and moderation; a paid model in the list would be
billed, so a free chain lists only `:free` ids), usage accounting (`usage.prompt_tokens`, `completion_tokens`, `cost`; always present) and limits (free models: 20
requests a minute, 50 a day or 1,000 a day after $10 of credit, one daily quota shared by every free model, failed attempts count; `GET /api/v1/key` returns
`data.free_model_daily_requests` with `used`, `limit` and `remaining`).

Plain httpx, no SDK, like the Anthropic provider. The provider does NOT retry across providers: the service falls to the paid Anthropic provider on any failure.
Unlike the Anthropic provider, NO OpenRouter failure stops the whole run: a bad key, an empty balance or a spent daily quota are all `transient`, because the
paid provider can still answer. A failure reason carries only the HTTP status and the error code, never a key, a prompt or a response body.

A request is sent with up to three free models (OpenRouter's fallback list takes at most three) and, if every one fails with a server-side error, once more with the
next three, at most two groups. Failed attempts count toward the daily free quota, so the provider reads the quota once, counts each request it sends, and stops
sending for the rest of the UTC day when it reaches zero. It also keeps under 20 requests a minute by waiting, not failing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import time
from collections import deque
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import httpx

from api.llm.chains import Chains
from api.llm.providers.base import FailureKind, ProviderFailure, TextSink
from api.llm.types import LLMRequest, ProviderResponse, Tier

log = logging.getLogger(__name__)

BASE_URL = "https://openrouter.ai/api/v1"
GROUP_SIZE = 3
MAX_GROUPS = 2
PER_MINUTE = 20
RATE_LIMIT_WAITS: tuple[float, ...] = (2.0, 5.0)
"""Seconds to wait before trying a rate-limited (429) request again, once per entry. A spent daily quota is not retried."""
REASONING_ALLOWANCE = 16384
"""Extra tokens a free reasoning model may spend thinking before it writes the reply (free, so it costs nothing). 2026-11-24: 4096 was too few for
the Plan (2000 + 4096 cut off at max_tokens on nemotron-3.5-super-vl), so the live demo could not plan a new question."""
PAID_REASONING_ALLOWANCE = 4096
"""The same allowance for a paid chain (V5-D26). It is billed, and the ledger reserves it as output, so it is kept small: Claude Haiku 5.5 thought for
2,351 tokens and Sonnet 5.5 for 1,287 on the real Plan request (2026-11-24)."""


def _groups(ids: tuple[str, ...]) -> list[list[str]]:
    return [list(ids[i : i + GROUP_SIZE]) for i in range(0, len(ids), GROUP_SIZE)][:MAX_GROUPS]


class Pacer:
    """At most `limit` requests in any 60 seconds: a burst waits for room instead of failing. The clock and the sleep are injectable so a test needs no real time."""

    def __init__(
        self,
        limit: int = PER_MINUTE,
        *,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self._limit = limit
        self._monotonic = monotonic
        self._sleep = sleep
        self._sent: deque[float] = deque()

    async def acquire(self) -> None:
        while True:
            now = self._monotonic()
            while self._sent and now - self._sent[0] >= 60.0:
                self._sent.popleft()
            if len(self._sent) < self._limit:
                self._sent.append(now)
                return
            await self._sleep(max(60.0 - (now - self._sent[0]), 0.05))


def _next_utc_midnight(now: datetime) -> datetime:
    return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


class OpenRouterProvider:
    name = "openrouter"

    def __init__(
        self,
        api_key: str,
        chains: Chains,
        *,
        allow_training: bool = True,
        base_url: str = BASE_URL,
        timeout_seconds: float = 300.0,
        client: httpx.AsyncClient | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        pacer: Pacer | None = None,
        rate_limit_waits: tuple[float, ...] = RATE_LIMIT_WAITS,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self._rate_limit_waits = rate_limit_waits
        self._sleep = sleep
        if not api_key:
            raise ValueError("an API key is required")
        self._key = api_key
        self._chains = chains
        self._allow_training = allow_training
        self._base = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)
        self._now = now
        self._pacer = pacer or Pacer()
        self._quota_known = False
        self._remaining: int | None = None
        """Free requests left today, as last read from OpenRouter and counted down by every request this provider sends. None: not read yet, or unreadable."""
        self._blocked_until: datetime | None = None

    def model_for(self, tier: Tier) -> str:  # noqa: ARG002
        """The first model of the default chain. The service prices and reserves against it (a free id costs nothing); the model that actually answered is the
        reply's own `model`, which goes to the ledger and the trace."""
        return self._chains.first()

    def model_for_request(self, request: LLMRequest) -> str:
        """The first model of the chain this request's purpose uses: what the service reserves against. For a paid chains file (V5-D26) the purposes may use
        different models at different prices, so the reservation must follow the purpose, not the default chain."""
        return self._chains.model_for_purpose(request.purpose)

    @property
    def paid(self) -> bool:
        return self._chains.paid

    @property
    def output_allowance(self) -> int:
        """Tokens this provider asks for beyond `request.max_tokens` (the reasoning allowance). The service reserves them too, so a paid cap is never under-reserved."""
        return PAID_REASONING_ALLOWANCE if self._chains.paid else REASONING_ALLOWANCE

    @property
    def free_requests_remaining(self) -> int | None:
        return self._remaining

    # ── the free daily quota ─────────────────────────────────────────────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json", "X-OpenRouter-Title": "Synapse"}

    async def _refresh_quota(self) -> None:
        """Read `GET /key` for the free-model quota. A failure here is not a failure of the call: the quota just stays unknown and is counted locally."""
        self._quota_known = True
        try:
            reply = await self._client.get(self._base + "/key", headers=self._headers())
            if reply.status_code != 200:
                return
            quota = reply.json()["data"]["free_model_daily_requests"]
            self._remaining = int(quota["remaining"])
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return
        if self._remaining <= 0:
            self._block_until_tomorrow()

    def _block_until_tomorrow(self) -> None:
        self._blocked_until = _next_utc_midnight(self._now())
        log.info("openrouter free quota spent until %s", self._blocked_until.isoformat())

    async def _check_quota(self) -> None:
        now = self._now()
        if self._blocked_until is not None and now >= self._blocked_until:
            self._blocked_until = None
            self._quota_known = False  # a new UTC day: read the quota again
            self._remaining = None
        if not self._quota_known:
            await self._refresh_quota()
        if self._blocked_until is not None:
            raise ProviderFailure(self.name, f"the free daily quota is spent until {self._blocked_until:%H:%M} UTC", "transient")

    def _count_one_request(self) -> None:
        if self._remaining is not None:
            self._remaining -= 1
            if self._remaining <= 0:
                self._block_until_tomorrow()

    # ── the call ─────────────────────────────────────────────────────────────────────────────────────────────────────────

    def _body(self, request: LLMRequest, group: list[str], *, stream: bool) -> dict:
        messages: list[dict] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})
        # The free models that answer reliably are reasoning models (2026-11-23: nemotron-3.5-super-vl, nemotron-3-ultra), and their hidden
        # reasoning counts against max_tokens: a short budget (the explanation's) was spent on thinking and cut off before any text
        # ("the reply was cut off at max_tokens"). Free tokens cost nothing, so the budget gets room for the reasoning on top, the effort
        # defaults to low, and the reasoning text is left out of the reply.
        if self._chains.paid:
            # Paid models (V5-D26, Claude through OpenRouter) are billed for every token, thinking included: a smaller allowance, no forced
            # reasoning effort, and no data-collection preference (a paid Anthropic endpoint does not train on requests).
            body: dict = {"models": group, "messages": messages, "max_tokens": request.max_tokens + PAID_REASONING_ALLOWANCE}
            if request.effort:
                body["reasoning"] = {"effort": request.effort, "exclude": True}
            if stream:
                body["stream"] = True
            return body
        body = {
            "models": group,
            "messages": messages,
            "max_tokens": request.max_tokens + REASONING_ALLOWANCE,
            "provider": {"data_collection": "allow" if self._allow_training else "deny"},
            "reasoning": {"effort": request.effort or "low", "exclude": True},
        }
        if stream:
            body["stream"] = True
        return body

    async def complete(self, request: LLMRequest, model: str, on_text: TextSink | None = None) -> ProviderResponse:  # noqa: ARG002
        if not self._chains.paid:  # the free daily quota counts free-model requests only; paid ones are bounded by the ledger's cap
            await self._check_quota()
        last: ProviderFailure | None = None
        for group in _groups(self._chains.for_purpose(request.purpose)):
            # A 429 that is not the spent daily quota is the free models' upstream throttling a burst (seen live 2026-11-23: the
            # explanation, sent a second after the route call, got 429 every time). A short wait clears it, so it is tried again a few
            # times before giving up; each try still counts toward the daily quota, and a spent quota is never retried.
            waits = list(self._rate_limit_waits)
            while True:
                await self._pacer.acquire()
                if not self._chains.paid:
                    self._count_one_request()
                try:
                    return await self._call(request, group, on_text)
                except _Stop as stop:  # account-level or rate-limit failure: another group would fail the same way
                    if stop.rate_limited and waits and self._blocked_until is None:
                        await self._sleep(waits.pop(0))
                        continue
                    raise stop.failure from None
                except ProviderFailure as failure:
                    if failure.kind in ("truncated", "timeout"):
                        raise
                    last = failure
                    break
        assert last is not None
        raise last

    async def _call(self, request: LLMRequest, group: list[str], on_text: TextSink | None) -> ProviderResponse:
        url = self._base + "/chat/completions"
        try:
            if on_text is None:
                reply = await self._client.post(url, headers=self._headers(), json=self._body(request, group, stream=False))
                if reply.status_code != 200:
                    raise await self._failure(reply)
                return self._read_whole(reply, request, group)
            return await self._stream(request, group, url, on_text)
        except httpx.TimeoutException as exc:
            raise ProviderFailure(self.name, "the request timed out", "timeout") from exc
        except httpx.HTTPError as exc:
            raise ProviderFailure(self.name, f"network error ({type(exc).__name__})", "transient") from exc

    def _read_whole(self, reply: httpx.Response, request: LLMRequest, group: list[str]) -> ProviderResponse:
        try:
            data = reply.json()
            if isinstance(data, dict) and "error" in data and "choices" not in data:
                raise ProviderFailure(self.name, f"error in the reply {_code(data)}", "transient")
            choice = data["choices"][0]
            text = _text(choice["message"].get("content"))
            finish = choice.get("finish_reason")
            usage = data.get("usage") or {}
            model = str(data.get("model") or group[0])
        except ProviderFailure:
            raise
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderFailure(self.name, "the reply was not a chat completion", "transient") from exc
        return self._finish(text, finish, usage, model, request)

    async def _stream(self, request: LLMRequest, group: list[str], url: str, on_text: TextSink) -> ProviderResponse:
        parts: list[str] = []
        usage: dict = {}
        finish = None
        model = group[0]
        async with self._client.stream("POST", url, headers=self._headers(), json=self._body(request, group, stream=True)) as reply:
            if reply.status_code != 200:
                await reply.aread()
                raise await self._failure(reply)
            async for line in reply.aiter_lines():
                if not line.startswith("data:"):
                    continue  # blank lines and ": OPENROUTER PROCESSING" comments
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload)
                except ValueError:
                    continue
                if not isinstance(chunk, dict):
                    continue
                if "error" in chunk:
                    raise ProviderFailure(self.name, f"stream error {_code(chunk)}", "transient")
                model = str(chunk.get("model") or model)
                if isinstance(chunk.get("usage"), dict):
                    usage = chunk["usage"]
                for choice in chunk.get("choices") or []:
                    delta = choice.get("delta") or {}
                    content = delta.get("content")
                    if isinstance(content, str) and content:
                        parts.append(content)
                        on_text(content)
                    finish = choice.get("finish_reason") or finish
        return self._finish("".join(parts), finish, usage, model, request)

    def _finish(self, text: str, finish: str | None, usage: dict, model: str, request: LLMRequest) -> ProviderResponse:
        tokens_in = _int(usage.get("prompt_tokens"))
        tokens_out = _int(usage.get("completion_tokens"))
        if tokens_in is None:
            tokens_in = math.ceil((len(request.prompt) + len(request.system or "")) / 4)
        if tokens_out is None:
            tokens_out = math.ceil(len(text) / 4)
        billed = {"tokens_in": tokens_in, "tokens_out": tokens_out}
        if finish == "length":
            raise ProviderFailure(self.name, "the reply was cut off at max_tokens", "truncated", **billed)
        if finish == "error":
            raise ProviderFailure(self.name, "the model reported an error while writing", "transient", **billed)
        if not text.strip():
            raise ProviderFailure(self.name, f"the reply had no text (finish_reason {finish})", "transient", **billed)
        cost = usage.get("cost")
        raw_details = usage.get("prompt_tokens_details")
        details = raw_details if isinstance(raw_details, dict) else {}
        return ProviderResponse(
            text=text,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=float(cost) if isinstance(cost, int | float) and cost >= 0 else None,
            cache_read_tokens=_int(details.get("cached_tokens")) or 0,
        )

    async def _failure(self, reply: httpx.Response) -> ProviderFailure | _Stop:
        """Map an HTTP error. Only the status and the error code are kept. No OpenRouter failure is fatal to the run (the paid provider may still answer), so
        the only kinds used are transient and timeout. 401, 402, 403 and 429 also stop this provider trying a second group, because it would fail the same way."""
        status = reply.status_code
        try:
            code = _code(reply.json())
        except ValueError:
            code = ""
        reason = f"HTTP {status}" + (f" {code}" if code else "")
        kind: FailureKind = "timeout" if status in (408, 504) else "transient"
        failure = ProviderFailure(self.name, reason, kind)
        if status == 429:
            await self._refresh_quota()  # was it the daily quota or the per-minute limit?
        if status in (401, 402, 403, 429):
            return _Stop(failure, rate_limited=status == 429)
        return failure


class _Stop(Exception):
    """Carries a failure that makes a second group pointless. `rate_limited`: it was a 429, which a short wait may clear."""

    def __init__(self, failure: ProviderFailure, *, rate_limited: bool = False):
        super().__init__(str(failure))
        self.failure = failure
        self.rate_limited = rate_limited


def _code(data: object) -> str:
    try:
        return str(data["error"]["code"])[:40]  # type: ignore[index]
    except (KeyError, TypeError):
        return ""


def _int(value: object) -> int | None:
    return int(value) if isinstance(value, int | float) and not isinstance(value, bool) and value >= 0 else None


def _text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(p.get("text", "")) for p in content if isinstance(p, dict) and p.get("type") == "text")
    return ""
