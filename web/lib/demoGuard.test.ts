import { beforeEach, describe, expect, it } from "vitest";

import { LIMITS, cleanId, cleanText, clientKey, rateLimited, readJsonBody, resetRateLimitsForTests } from "./demoGuard";

beforeEach(() => resetRateLimitsForTests());

const post = (body: string, type = "application/json") =>
  new Request("http://x/demo-api/chat", { method: "POST", headers: { "content-type": type }, body });

describe("rateLimited", () => {
  it("allows the limit in a window, then asks the visitor to wait", () => {
    const now = 1_000_000;
    for (let i = 0; i < LIMITS.replay; i++) expect(rateLimited("a", "replay", now)).toBeNull();
    const wait = rateLimited("a", "replay", now);
    expect(wait).toBeGreaterThan(0);
    expect(wait).toBeLessThanOrEqual(60);
  });

  it("keeps visitors and buckets apart, and frees the window after a minute", () => {
    const now = 2_000_000;
    for (let i = 0; i < LIMITS.replay; i++) rateLimited("a", "replay", now);
    expect(rateLimited("b", "replay", now)).toBeNull();
    expect(rateLimited("a", "read", now)).toBeNull();
    expect(rateLimited("a", "replay", now + LIMITS.windowMs + 1)).toBeNull();
  });
});

describe("clientKey", () => {
  it("takes the first forwarded address", () => {
    const r = new Request("http://x/", { headers: { "x-forwarded-for": "203.0.113.7, 10.0.0.1" } });
    expect(clientKey(r)).toBe("203.0.113.7");
  });
});

describe("cleanText", () => {
  it("removes control and invisible characters and trims", () => {
    expect(cleanText("  what\u0000 is​ RRF?\u0007 ", 100)).toBe("what is RRF?");
  });
  it("keeps newlines and tabs", () => {
    expect(cleanText("a\nb\tc", 100)).toBe("a\nb\tc");
  });
  it("refuses empty, too long and non-text values", () => {
    expect(cleanText("   ", 10)).toBeNull();
    expect(cleanText("x".repeat(11), 10)).toBeNull();
    expect(cleanText(42, 10)).toBeNull();
    expect(cleanText({ toString: () => "x" }, 10)).toBeNull();
  });
});

describe("cleanId", () => {
  it("accepts plain ids", () => {
    expect(cleanId("claim-1000~graph_based_rag")).toBe("claim-1000~graph_based_rag");
    expect(cleanId("turn-472e7ebe5686")).toBe("turn-472e7ebe5686");
  });
  it("refuses traversal, markup, spaces and over-long ids", () => {
    for (const bad of ["../etc", "a/b", "<script>", "a b", "__proto__x\u0000", "x".repeat(201), "", 7]) expect(cleanId(bad)).toBeNull();
  });
});

describe("readJsonBody", () => {
  it("reads a JSON object", async () => {
    const r = await readJsonBody(post('{"message":"hi"}'));
    expect(r).toEqual({ ok: true, body: { message: "hi" } });
  });
  it("refuses other content types, bad JSON, arrays and oversized bodies", async () => {
    expect(await readJsonBody(post("message=hi", "application/x-www-form-urlencoded"))).toMatchObject({ ok: false, status: 415 });
    expect(await readJsonBody(post("{nope"))).toMatchObject({ ok: false, status: 400 });
    expect(await readJsonBody(post("[1,2]"))).toMatchObject({ ok: false, status: 400 });
    expect(await readJsonBody(post(JSON.stringify({ message: "x".repeat(LIMITS.bodyBytes) })))).toMatchObject({ ok: false, status: 413 });
  });
});
