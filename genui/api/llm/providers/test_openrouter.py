"""The OpenRouter provider against a mock transport: no socket is opened and nothing is billed. The reply shapes are those in OpenRouter's docs, read 2026-11-14
(chat completions, streaming, errors, model fallbacks, usage accounting, limits)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest

from api.llm.chains import parse_chains
from api.llm.pricing import price_for
from api.llm.providers.base import ProviderFailure
from api.llm.providers.openrouter import BASE_URL, REASONING_ALLOWANCE, OpenRouterProvider, Pacer
from api.llm.types import LLMRequest

KEY = "or-test-key-not-a-real-credential"
FAST = ["n/fast1:free", "n/fast2:free", "n/fast3:free"]
CHAINS = parse_chains(
    {
        "chains": {"fast": FAST, "big": [f"n/big{i}:free" for i in range(1, 6)]},
        "purposes": {"explain": "fast", "free": "big"},
        "default": "fast",
    }
)
REQ = LLMRequest(prompt="Why does a spring stretch?", purpose="explain", system="Be brief.", max_tokens=200)


class Server:
    """A scripted OpenRouter: records every request, answers the key lookup, and hands each chat request to `chat`."""

    def __init__(self, chat, *, remaining: int | None = 50, key_status: int = 200):  # noqa: ANN001
        self.chat = chat
        self.remaining = remaining
        self.key_status = key_status
        self.posts: list[dict] = []
        self.key_gets = 0
        self.headers: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path.endswith("/key"):
            self.key_gets += 1
            if self.key_status != 200:
                return httpx.Response(self.key_status, json={"error": {"code": self.key_status}})
            left = 0 if self.remaining is None else self.remaining
            return httpx.Response(200, json={"data": {"free_model_daily_requests": {"used": 50 - left, "limit": 50, "remaining": left}}})
        assert request.url.path.endswith("/chat/completions"), request.url
        body = json.loads(request.content)
        self.posts.append(body)
        self.headers.append(dict(request.headers))
        return self.chat(len(self.posts) - 1, body)


def make(server: Server, chains=CHAINS, **kw) -> OpenRouterProvider:  # noqa: ANN001
    client = httpx.AsyncClient(transport=httpx.MockTransport(server))
    return OpenRouterProvider(KEY, chains, client=client, **kw)


def ok(text: str = "hello", *, model: str = "n/fast2:free", finish: str = "stop", **usage) -> httpx.Response:  # noqa: ANN003
    return httpx.Response(
        200,
        json={
            "id": "gen-1",
            "model": model,
            "choices": [{"finish_reason": finish, "index": 0, "message": {"role": "assistant", "content": text}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 5, "cost": 0, **usage},
        },
    )


def sse(*chunks: dict | str) -> httpx.Response:
    lines = [c if isinstance(c, str) else f"data: {json.dumps(c)}" for c in chunks]
    return httpx.Response(200, content=("\n\n".join(lines) + "\n\n").encode(), headers={"content-type": "text/event-stream"})


def error(status: int, message: str = "nope") -> httpx.Response:
    return httpx.Response(status, json={"error": {"code": status, "message": message, "metadata": {"raw": KEY}}})


# ── a good reply ──────────────────────────────────────────────────────────────────────────────────────────────────────


async def test_a_good_reply_has_the_documented_request_shape_and_names_the_model_that_answered() -> None:
    server = Server(lambda i, b: ok("A spring stretches.", prompt_tokens_details={"cached_tokens": 4}))
    result = await make(server).complete(REQ, "n/fast1:free")
    assert result.text == "A spring stretches." and (result.tokens_in, result.tokens_out) == (12, 5)
    assert result.model == "n/fast2:free", "the ledger records the model that answered, not the first one asked"
    assert result.cost_usd == 0.0 and result.cache_read_tokens == 4
    body = server.posts[0]
    assert body["models"] == FAST and "model" not in body, "the free chain goes in one request, in order"
    assert body["messages"] == [{"role": "system", "content": "Be brief."}, {"role": "user", "content": "Why does a spring stretch?"}]
    # The reply budget plus room for a free reasoning model's hidden thinking; low effort, reasoning text excluded (2026-11-23).
    assert body["max_tokens"] == 200 + REASONING_ALLOWANCE and body["provider"] == {"data_collection": "allow"} and "stream" not in body
    assert body["reasoning"] == {"effort": "low", "exclude": True}
    assert server.headers[0]["authorization"] == f"Bearer {KEY}"


async def test_training_providers_can_be_excluded_and_effort_is_passed_as_reasoning() -> None:
    server = Server(lambda i, b: ok())
    request = LLMRequest(prompt="p", purpose="explain", effort="low", max_tokens=50)
    await make(server, allow_training=False).complete(request, "x")
    assert server.posts[0]["provider"] == {"data_collection": "deny"} and server.posts[0]["reasoning"] == {"effort": "low", "exclude": True}


async def test_a_purpose_uses_its_own_chain() -> None:
    server = Server(lambda i, b: ok(model="n/big1:free"))
    await make(server).complete(LLMRequest(prompt="p", purpose="free", max_tokens=50), "x")
    assert server.posts[0]["models"] == ["n/big1:free", "n/big2:free", "n/big3:free"]


def test_the_model_asked_for_is_free_so_the_ledger_reserves_nothing() -> None:
    provider = make(Server(lambda i, b: ok()))
    model = provider.model_for("heavy")
    assert model.endswith(":free") and price_for("openrouter", model) == (0.0, 0.0)
    assert price_for("openrouter", "anthropic/claude-sonnet-5-5") != (0.0, 0.0), "a model that is not free is never priced at zero"


def test_a_key_is_required() -> None:
    with pytest.raises(ValueError):
        OpenRouterProvider("", CHAINS)


# ── streaming ─────────────────────────────────────────────────────────────────────────────────────────────────────────


async def test_a_streamed_reply_hands_over_text_as_it_arrives_and_reads_usage_from_the_last_chunk() -> None:
    def chat(i: int, body: dict) -> httpx.Response:
        assert body["stream"] is True
        return sse(
            ": OPENROUTER PROCESSING",
            {"model": "n/fast1:free", "choices": [{"delta": {"reasoning": "thinking about springs"}}]},
            {"model": "n/fast1:free", "choices": [{"delta": {"content": "A spring "}}]},
            {"model": "n/fast1:free", "choices": [{"delta": {"content": "stretches."}, "finish_reason": "stop"}]},
            {"model": "n/fast1:free", "choices": [], "usage": {"prompt_tokens": 30, "completion_tokens": 9, "cost": 0}},
            "data: [DONE]",
        )

    pieces: list[str] = []
    result = await make(Server(chat)).complete(REQ, "x", on_text=pieces.append)
    assert pieces == ["A spring ", "stretches."], "reasoning text is not the reply and is not handed over"
    assert result.text == "A spring stretches." and (result.tokens_in, result.tokens_out) == (30, 9) and result.model == "n/fast1:free"


async def test_a_streamed_reply_without_usage_is_estimated_not_refused() -> None:
    server = Server(lambda i, b: sse({"model": "n/fast1:free", "choices": [{"delta": {"content": "abcdefgh"}, "finish_reason": "stop"}]}, "data: [DONE]"))
    result = await make(server).complete(REQ, "x", on_text=lambda s: None)
    assert result.text == "abcdefgh" and result.tokens_out == 2 and result.tokens_in > 0 and result.cost_usd is None


async def test_an_error_that_arrives_after_streaming_started_is_a_failure() -> None:
    server = Server(
        lambda i, b: sse({"choices": [{"delta": {"content": "part"}}]}, {"error": {"code": 502, "message": "upstream"}, "choices": [{"finish_reason": "error"}]})
    )
    with pytest.raises(ProviderFailure) as err:
        await make(server).complete(REQ, "x", on_text=lambda s: None)
    assert err.value.kind == "transient" and "502" in err.value.reason


# ── replies that are not a good reply ─────────────────────────────────────────────────────────────────────────────────


async def test_a_reply_cut_off_at_max_tokens_is_truncated_and_keeps_its_usage() -> None:
    server = Server(lambda i, b: ok("", finish="length", completion_tokens=200))
    with pytest.raises(ProviderFailure) as err:
        await make(server).complete(REQ, "x")
    assert err.value.kind == "truncated" and err.value.tokens_out == 200 and len(server.posts) == 1, "a second group would write the same too-long reply"


@pytest.mark.parametrize(
    "reply",
    [
        ok("   ", finish="stop"),
        ok("text", finish="error"),
        httpx.Response(200, json={"error": {"code": 502, "message": "boom"}}),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, content=b"<html>not json</html>"),
    ],
)
async def test_an_empty_errored_or_malformed_reply_is_transient_so_the_paid_provider_can_answer(reply: httpx.Response) -> None:
    server = Server(lambda i, b: reply)
    with pytest.raises(ProviderFailure) as err:
        await make(server).complete(REQ, "x")
    assert err.value.kind == "transient"


# ── HTTP errors: none is fatal to the run ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("status", [401, 402, 403])
async def test_an_account_level_error_is_transient_not_fatal_and_is_not_tried_again(status: int) -> None:
    """The Anthropic provider treats 401 and 402 as fatal; here the paid provider may still answer, so they must not stop the run."""
    server = Server(lambda i, b: error(status))
    with pytest.raises(ProviderFailure) as err:
        await make(server).complete(REQ, "x")
    assert err.value.kind == "transient" and err.value.reason == f"HTTP {status} {status}"
    assert len(server.posts) == 1


async def test_a_short_rate_limit_is_waited_out_and_tried_again() -> None:
    """Seen live (2026-11-23): free models throttle a burst with 429 while the daily quota is fine. A short wait clears it."""
    server = Server(lambda i, b: error(429) if i == 0 else ok("a spring stretches"), remaining=30)
    waited: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        waited.append(seconds)

    result = await make(server, rate_limit_waits=(2.0, 5.0), sleep=fake_sleep).complete(REQ, "x")
    assert result.text == "a spring stretches" and waited == [2.0] and len(server.posts) == 2


async def test_a_rate_limit_rereads_the_quota_and_a_spent_daily_quota_blocks_the_rest_of_the_day() -> None:
    now = [datetime(2026, 11, 14, 10, 0, tzinfo=UTC)]
    server = Server(lambda i, b: error(429), remaining=5)
    provider = make(server, now=lambda: now[0], rate_limit_waits=())  # no waits: this test is about the quota, not the retry
    with pytest.raises(ProviderFailure) as err:
        await provider.complete(REQ, "x")
    assert err.value.kind == "transient" and server.key_gets == 2, "once before the call, once after the 429"
    assert len(server.posts) == 1
    server.remaining = 0
    with pytest.raises(ProviderFailure):
        await provider.complete(REQ, "x")  # this 429 finds the quota spent
    posts_before = len(server.posts)
    with pytest.raises(ProviderFailure) as blocked:
        await provider.complete(REQ, "x")
    assert "spent" in blocked.value.reason and len(server.posts) == posts_before, "no request is sent while the quota is spent"
    now[0] = datetime(2026, 11, 15, 0, 0, 1, tzinfo=UTC)  # a new UTC day
    server.chat = lambda i, b: ok()
    server.remaining = 50
    assert (await provider.complete(REQ, "x")).text == "hello"


async def test_a_server_side_failure_tries_the_next_group_of_three_and_no_more_than_two() -> None:
    def chat(i: int, body: dict) -> httpx.Response:
        return error(502) if i == 0 else ok(model="n/big4:free")

    server = Server(chat)
    result = await make(server).complete(LLMRequest(prompt="p", purpose="free", max_tokens=50), "x")
    assert [p["models"] for p in server.posts] == [["n/big1:free", "n/big2:free", "n/big3:free"], ["n/big4:free", "n/big5:free"]]
    assert result.model == "n/big4:free"
    always = Server(lambda i, b: error(503))
    with pytest.raises(ProviderFailure):
        await make(always).complete(LLMRequest(prompt="p", purpose="free", max_tokens=50), "x")
    assert len(always.posts) == 2


async def test_a_timeout_is_a_timeout_and_a_network_error_is_transient() -> None:
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    for handler, kind in ((slow, "timeout"), (down, "transient")):
        provider = OpenRouterProvider(KEY, CHAINS, client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        provider._quota_known = True  # noqa: SLF001  # the key lookup is not what is under test
        with pytest.raises(ProviderFailure) as err:
            await provider.complete(REQ, "x")
        assert err.value.kind == kind


async def test_a_failure_never_carries_the_key_the_prompt_or_the_response_body() -> None:
    server = Server(lambda i, b: error(401, message=f"bad key {KEY} for prompt Why does a spring stretch?"))
    with pytest.raises(ProviderFailure) as err:
        await make(server).complete(REQ, "x")
    text = str(err.value) + err.value.reason
    assert KEY not in text and "spring" not in text and "bad key" not in text


# ── the free daily quota and the pace ─────────────────────────────────────────────────────────────────────────────────


async def test_a_spent_quota_sends_nothing_and_each_request_is_counted_down() -> None:
    server = Server(lambda i, b: ok(), remaining=2)
    provider = make(server)
    await provider.complete(REQ, "x")
    assert provider.free_requests_remaining == 1
    await provider.complete(REQ, "x")
    with pytest.raises(ProviderFailure) as err:
        await provider.complete(REQ, "x")
    assert "spent" in err.value.reason and len(server.posts) == 2 and server.key_gets == 1, "the quota is read once and counted locally"
    empty = Server(lambda i, b: ok(), remaining=0)
    with pytest.raises(ProviderFailure):
        await make(empty).complete(REQ, "x")
    assert empty.posts == []


async def test_an_unreadable_quota_does_not_stop_a_call() -> None:
    server = Server(lambda i, b: ok(), key_status=500)
    provider = make(server)
    assert (await provider.complete(REQ, "x")).text == "hello" and provider.free_requests_remaining is None


async def test_the_pacer_waits_instead_of_failing_when_the_minute_is_full() -> None:
    clock = [0.0]
    slept: list[float] = []

    async def sleep(seconds: float) -> None:
        slept.append(seconds)
        clock[0] += seconds

    pacer = Pacer(2, monotonic=lambda: clock[0], sleep=sleep)
    await pacer.acquire()
    clock[0] = 10.0
    await pacer.acquire()
    await pacer.acquire()  # the minute that began at 0 is full: wait for room
    assert slept == [50.0] and clock[0] == 60.0


def test_the_base_url_is_openrouters_api() -> None:
    assert BASE_URL == "https://openrouter.ai/api/v1"
