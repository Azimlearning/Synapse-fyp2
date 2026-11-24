// The hosted demo's backend (NEXT_PUBLIC_DEMO=1 builds only): it replays the real GraphRAG API's responses, recorded from the
// local server on the 16-paper corpus by demo/record/record_graphrag.py into web/demo-data/graphrag/. No model is called and
// nothing is stored. Built with NEXT_PUBLIC_API_BASE_URL=/demo-api, the app talks to this route exactly as it talks to the API.
//
// GET views are served as recorded. A chat question is matched to a recorded one (word for word, else a close match on its
// content words) and its SSE frames are replayed with the recorded pacing, compressed. Writes the demo cannot make (upload,
// new labs, saved views) answer with an ErrorEnvelope that says why. Quiz answers are checked against the recorded right answer.

import { promises as fs } from "node:fs";
import path from "node:path";

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
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });

function envelope(code: string, message: string, status: number, retryable = false) {
  return json({ code, message, issues: [], retryable }, status);
}

const DEMO_ONLY =
  "This is the hosted demo: it replays answers recorded from the real system on its 16 research papers, so it cannot change anything. " +
  "Run Synapse locally (github.com/Azimlearning/Synapse-fyp2) to upload your own documents.";

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
  return new Response(body, { status: hit.status, headers: { "content-type": "application/json", "cache-control": "no-store" } });
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
    headers: { "content-type": "text/event-stream", "cache-control": "no-cache, no-transform", "x-accel-buffering": "no" },
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
const pathOf = async (ctx: Ctx) => "/" + (await ctx.params).path.map(encodeURIComponent).join("/");

export async function GET(request: Request, ctx: Ctx): Promise<Response> {
  if (!ENABLED) return new Response("Not found", { status: 404 });
  const pathname = await pathOf(ctx);
  const search = new URL(request.url).searchParams;
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

  if (pathname === "/chat") {
    let message = "";
    try {
      message = String(((await request.json()) as { message?: unknown }).message ?? "");
    } catch {
      return envelope("bad_request", "The request is not JSON.", 400);
    }
    if (!message.trim()) return envelope("bad_request", "The message is empty.", 400);
    const entry = await findChat(message);
    if (!entry) return notRecorded();
    const recorded = await readJson<{ frames: Frame[] }>(entry.file);
    return sseResponse(recorded.frames);
  }

  if (pathname === "/quiz/answer") {
    const body = (await request.json().catch(() => ({}))) as { itemId?: string; chosenId?: string };
    const answers = await readJson<Record<string, QuizAnswer>>("quiz_answers.json");
    const known = body.itemId ? answers[body.itemId] : undefined;
    if (!known || !body.chosenId) return envelope("not_found", "This question's answer was not recorded in the hosted demo.", 404);
    const correct = body.chosenId === known.answer.id;
    return json({
      itemId: body.itemId,
      correct,
      answer: known.answer,
      citation: known.citation,
      // Nothing is stored in the demo, so mastery is shown as after this one answer.
      mastery: { score: correct ? 0.6 : 0.2, events: 1 },
    });
  }

  if (pathname === "/learner/events") {
    const body = (await request.json().catch(() => ({}))) as { pageId?: string };
    return json({ pageId: body.pageId ?? "", mastery: { score: 0.5, events: 1 } });
  }

  return envelope("bad_request", DEMO_ONLY, 400);
}

export async function DELETE(_request: Request, _ctx: Ctx): Promise<Response> {
  if (!ENABLED) return new Response("Not found", { status: 404 });
  return envelope("bad_request", DEMO_ONLY, 400);
}
