// Guards for the hosted demo's public replay route. No model is called there, so nothing can be spent, but the route is public:
// it limits how often one visitor can call it, refuses oversized or malformed input, and cleans the text it does accept. The same
// file is in web/lib/demoGuard.ts (the Synapse app).
//
// The rate limit is a sliding window kept in this server instance's memory. On Vercel each instance keeps its own window, so a
// visitor spread across instances gets more than the stated limit; it stops a single tab or script hammering one instance, which is
// all a replay route needs. Use a shared store (Vercel KV, Upstash) if a real model is ever put behind it.

export const LIMITS = {
  /** POSTs that replay a chat turn or a simulation, per visitor per minute. */
  replay: 20,
  /** Every other request, per visitor per minute. */
  read: 240,
  windowMs: 60_000,
  /** Largest JSON body accepted, in bytes. */
  bodyBytes: 16_384,
  /** Longest question, in characters (the real API's limit). */
  messageChars: 4_000,
  /** Longest id or search, in characters. */
  idChars: 200,
};

const hits = new Map<string, number[]>();

/** The visitor's address as Vercel reports it (the first hop of x-forwarded-for), or "local". */
export function clientKey(request: Request): string {
  const fwd = request.headers.get("x-forwarded-for");
  const first = fwd?.split(",")[0]?.trim();
  return first || request.headers.get("x-real-ip") || "local";
}

/** Count one request for `key` in `bucket`; returns the seconds to wait when over `limit`, else null. */
export function rateLimited(key: string, bucket: "replay" | "read", now = Date.now()): number | null {
  const limit = LIMITS[bucket];
  const id = `${bucket}:${key}`;
  const recent = (hits.get(id) ?? []).filter((t) => now - t < LIMITS.windowMs);
  if (recent.length >= limit) {
    hits.set(id, recent);
    return Math.max(1, Math.ceil((LIMITS.windowMs - (now - recent[0]!)) / 1000));
  }
  recent.push(now);
  hits.set(id, recent);
  if (hits.size > 10_000) {
    // Keep memory bounded: drop windows that have gone quiet.
    for (const [k, times] of hits) if (times.every((t) => now - t >= LIMITS.windowMs)) hits.delete(k);
  }
  return null;
}

export const resetRateLimitsForTests = () => hits.clear();

/** Text from a visitor: control characters (other than tab and newline) removed, spaces collapsed at the ends, length capped. */
export function cleanText(value: unknown, max: number): string | null {
  if (typeof value !== "string") return null;
  // eslint-disable-next-line no-control-regex
  const cleaned = value.normalize("NFC").replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F\u200B-\u200F\u2028-\u202E\u2060-\u2064\uFEFF]/g, "").trim();
  if (!cleaned || cleaned.length > max) return null;
  return cleaned;
}

const ID = /^[A-Za-z0-9_.~:-]+$/;

/** An id from a path, a query or a body: letters, digits and _ . ~ : - only, and not too long. */
export function cleanId(value: unknown): string | null {
  if (typeof value !== "string" || value.length === 0 || value.length > LIMITS.idChars) return null;
  return ID.test(value) ? value : null;
}

export type JsonResult = { ok: true; body: Record<string, unknown> } | { ok: false; status: number; message: string };

/** Read a JSON object body: the content type must be JSON and the body no larger than LIMITS.bodyBytes. */
export async function readJsonBody(request: Request): Promise<JsonResult> {
  const type = request.headers.get("content-type") ?? "";
  if (!type.toLowerCase().includes("application/json")) return { ok: false, status: 415, message: "Send the request as JSON." };
  const declared = Number(request.headers.get("content-length") ?? "0");
  if (declared > LIMITS.bodyBytes) return { ok: false, status: 413, message: "The request is too large." };
  const text = await request.text();
  if (new TextEncoder().encode(text).length > LIMITS.bodyBytes) return { ok: false, status: 413, message: "The request is too large." };
  try {
    const body: unknown = JSON.parse(text);
    if (!body || typeof body !== "object" || Array.isArray(body)) return { ok: false, status: 400, message: "The request must be a JSON object." };
    return { ok: true, body: body as Record<string, unknown> };
  } catch {
    return { ok: false, status: 400, message: "The request is not valid JSON." };
  }
}

/** Headers every replay response carries. */
export const SAFE_HEADERS: Record<string, string> = {
  "x-content-type-options": "nosniff",
  "cache-control": "no-store",
  "referrer-policy": "strict-origin-when-cross-origin",
};

export function tooMany(retryAfter: number): Response {
  return new Response(
    JSON.stringify({
      code: "bad_request",
      message: `Too many requests from this browser. Try again in ${retryAfter} seconds.`,
      issues: [],
      retryable: true,
    }),
    { status: 429, headers: { ...SAFE_HEADERS, "content-type": "application/json", "retry-after": String(retryAfter) } },
  );
}
