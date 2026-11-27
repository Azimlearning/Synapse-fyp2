// The hosted demo's backend (NEXT_PUBLIC_DEMO=1 builds only): it replays the real GraphRAG API's responses, recorded from the
// local server on the 16-paper corpus by demo/record/record_graphrag.py into web/demo-data/graphrag/. No model is called and
// nothing is stored. Built with NEXT_PUBLIC_API_BASE_URL=/demo-api, the app talks to this route exactly as it talks to the API.
//
// GET views are served as recorded. A chat question is matched to a recorded one (word for word, else a close match on its
// content words) and its SSE frames are replayed with the recorded pacing, compressed. Writes the demo cannot make (upload,
// new labs, saved views) answer with an ErrorEnvelope that says why. Quiz answers are checked against the recorded right answer.

import { promises as fs } from "node:fs";
import path from "node:path";

import { LIMITS, SAFE_HEADERS, cleanId, cleanText, clientKey, rateLimited, readJsonBody, tooMany } from "@/lib/demoGuard";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ENABLED = process.env.NEXT_PUBLIC_DEMO === "1";
const DATA = path.join(process.cwd(), "demo-data", "graphrag");

type Route = { status: number; file: string };
type ChatEntry = { question: string; file: string; turns: string[] };
type Frame = { t: number; data: string };
type QuizAnswer = { answer: { id: string } & Record<string, unknown>; citation: unknown };

const cache = new Map<string, unknown>();
async function readJson<T>(rel: string): Promise<T> {
  if (!cache.has(rel)) cache.set(rel, JSON.parse(await fs.readFile(path.join(DATA, rel), "utf-8")));
  return cache.get(rel) as T;
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { ...SAFE_HEADERS, "content-type": "application/json" } });

function envelope(code: string, message: string, status: number, retryable = false) {
  return json({ code, message, issues: [], retryable }, status);
}

const DEMO_ONLY =
  "This is the hosted demo: it replays answers recorded from the real system on 16 sample research papers, so it cannot change anything. " +
  "In your own copy of Synapse (github.com/Azimlearning/Synapse-fyp2) you can delete the samples and upload your own documents.";

function keyOf(method: string, pathname: string, search: URLSearchParams): string {
  const q = [...search.entries()].sort(([a], [b]) => a.localeCompare(b));
  const qs = new URLSearchParams(q).toString();
  return `${method} ${pathname}${qs ? `?${qs}` : ""}`;
}

async function replayGet(key: string): Promise<Response | null> {
  const routes = await readJson<Record<string, Route>>("routes.json");
  const hit = routes[key];
  if (!hit) return null;
  const body = await fs.readFile(path.join(DATA, hit.file), "utf-8");
  return new Response(body, { status: hit.status, headers: { ...SAFE_HEADERS, "content-type": "application/json" } });
}

// ── chat matching ────────────────────────────────────────────────────────────

const STOP = new Set(
  "a an the of on in for to and or is are was were be what which how why who does do did can could would should it its this that these those me my i you your with by from about as at into across between their there".split(
    " ",
  ),
);
const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9\s-]/g, " ").replace(/\s+/g, " ").trim();
const words = (s: string) => new Set(norm(s).split(" ").filter((w) => w && !STOP.has(w)));

function similarity(a: string, b: string): number {
  const x = words(a);
  const y = words(b);
  if (x.size === 0 || y.size === 0) return 0;
  let both = 0;
  for (const w of x) if (y.has(w)) both++;
  return both / (x.size + y.size - both);
}

async function findChat(question: string): Promise<ChatEntry | null> {
  const index = await readJson<ChatEntry[]>("chat/index.json");
  const exact = index.find((e) => norm(e.question) === norm(question));
  if (exact) return exact;
  let best: ChatEntry | null = null;
  let score = 0;
  for (const e of index) {
    const s = similarity(question, e.question);
    if (s > score) [best, score] = [e, s];
  }
  return score >= 0.6 ? best : null;
}

function sseResponse(frames: Frame[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      let last = 0;
      for (const f of frames) {
        // The recorded pacing, compressed so a long turn still finishes in a few seconds.
        const wait = Math.min(Math.max(0, f.t - last) * 0.25, 900);
        last = f.t;
        if (wait > 0) await new Promise((r) => setTimeout(r, wait));
        controller.enqueue(encoder.encode(`${f.data}\n\n`));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    headers: { ...SAFE_HEADERS, "content-type": "text/event-stream", "cache-control": "no-cache, no-transform", "x-accel-buffering": "no" },
  });
}

async function notRecorded(): Promise<Response> {
  const index = await readJson<ChatEntry[]>("chat/index.json");
  const sample = index
    .map((e) => e.question)
    .filter((q) => !/^(quiz me|make |give me|guide me|brief me|write |show my|what should)/i.test(q))
    .slice(0, 4)
    .map((q) => `"${q}"`)
    .join(", ");
  const error = {
    code: "not_found",
    message:
      "This hosted demo replays answers recorded from the real system, and that question was not one of them. " +
      `Try a question from the welcome card, a Studio tool, or for example ${sample}. ` +
      "Run Synapse locally to ask anything about your own documents.",
    issues: [],
    retryable: false,
  };
  return sseResponse([{ t: 0, data: `data: ${JSON.stringify({ type: "error", error })}` }]);
}

// ── handlers ─────────────────────────────────────────────────────────────────

type Ctx = { params: Promise<{ path: string[] }> };

/** The path, or null when it is too deep or a segment is not a plain id (no traversal, no odd characters). */
async function pathOf(ctx: Ctx): Promise<string | null> {
  const parts = (await ctx.params).path;
  if (parts.length === 0 || parts.length > 4) return null;
  const clean = parts.map(cleanId);
  return clean.every((p) => p !== null) ? "/" + clean.join("/") : null;
}

/** Query parameters the API takes: `page` (an id) and `query` (text). Anything else, or a bad value, is refused. */
function cleanSearch(raw: URLSearchParams): URLSearchParams | null {
  const out = new URLSearchParams();
  for (const [k, v] of raw) {
    if (k === "page") {
      const id = cleanId(v);
      if (!id) return null;
      out.set(k, id);
    } else if (k === "query") {
      const text = cleanText(v, LIMITS.idChars);
      if (!text) return null;
      out.set(k, text);
    } else {
      return null;
    }
  }
  return out;
}

export async function GET(request: Request, ctx: Ctx): Promise<Response> {
  if (!ENABLED) return new Response("Not found", { status: 404 });
  const wait = rateLimited(clientKey(request), "read");
  if (wait) return tooMany(wait);
  const pathname = await pathOf(ctx);
  const search = cleanSearch(new URL(request.url).searchParams);
  if (!pathname || !search) return envelope("bad_request", "That request is not part of the hosted demo.", 400);
  const hit = await replayGet(keyOf("GET", pathname, search));
  if (hit) return hit;

  if (pathname === "/vault/notes" || pathname === "/vault/quiz") {
    // A search or a page that was not recorded: the closest recorded search, else the whole notes view.
    const query = search.get("query");
    if (query && !search.get("page")) {
      const routes = await readJson<Record<string, Route>>("routes.json");
      const prefix = `GET ${pathname}?query=`;
      const recorded = Object.keys(routes).filter((k) => k.startsWith(prefix));
      const close = recorded.find((k) => norm(decodeURIComponent(k.slice(prefix.length).replace(/\+/g, " "))).includes(norm(query)));
      if (close) return (await replayGet(close))!;
    }
    if (search.get("page")) {
      return envelope("not_found", "This concept page is not in the hosted demo's recording. Open one of the larger concepts on the graph.", 404);
    }
    return (await replayGet(`GET ${pathname}`)) ?? envelope("not_found", "Not recorded.", 404);
  }
  if (pathname.startsWith("/turns/")) {
    return envelope("not_found", "The trace of this turn was not recorded.", 404);
  }
  return envelope("not_found", "This view is not part of the hosted demo.", 404);
}

export async function POST(request: Request, ctx: Ctx): Promise<Response> {
  if (!ENABLED) return new Response("Not found", { status: 404 });
  const pathname = await pathOf(ctx);
  const wait = rateLimited(clientKey(request), pathname === "/chat" ? "replay" : "read");
  if (wait) return tooMany(wait);
  if (pathname !== "/chat" && pathname !== "/quiz/answer" && pathname !== "/learner/events") return envelope("bad_request", DEMO_ONLY, 400);

  const read = await readJsonBody(request);
  if (!read.ok) return envelope("bad_request", read.message, read.status);
  const body = read.body;

  if (pathname === "/chat") {
    const message = cleanText(body.message, LIMITS.messageChars);
    if (!message) return envelope("bad_request", `Ask a question of 1 to ${LIMITS.messageChars} characters.`, 400);
    if (body.history !== undefined && (!Array.isArray(body.history) || body.history.length > 20)) {
      return envelope("bad_request", "The history is too long.", 400);
    }
    const entry = await findChat(message);
    if (!entry) return notRecorded();
    const recorded = await readJson<{ frames: Frame[] }>(entry.file);
    return sseResponse(recorded.frames);
  }

  if (pathname === "/quiz/answer") {
    const itemId = cleanId(body.itemId);
    const chosenId = cleanId(body.chosenId);
    if (!itemId || !chosenId) return envelope("validation_failed", "The answer needs a question id and a choice.", 422);
    const answers = await readJson<Record<string, QuizAnswer>>("quiz_answers.json");
    const known = Object.hasOwn(answers, itemId) ? answers[itemId] : undefined;
    if (!known) return envelope("not_found", "This question's answer was not recorded in the hosted demo.", 404);
    const correct = chosenId === known.answer.id;
    return json({
      itemId,
      correct,
      answer: known.answer,
      citation: known.citation,
      // Nothing is stored in the demo, so mastery is shown as after this one answer.
      mastery: { score: correct ? 0.6 : 0.2, events: 1 },
    });
  }

  // /learner/events: a self-rating; the demo stores nothing.
  const pageId = cleanId(body.pageId);
  if (!pageId) return envelope("validation_failed", "The rating needs a page id.", 422);
  return json({ pageId, mastery: { score: 0.5, events: 1 } });
}

export async function DELETE(request: Request, _ctx: Ctx): Promise<Response> {
  if (!ENABLED) return new Response("Not found", { status: 404 });
  const wait = rateLimited(clientKey(request), "read");
  if (wait) return tooMany(wait);
  return envelope("bad_request", DEMO_ONLY, 400);
}
