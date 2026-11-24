// The hosted demo's backend for the simulation engine (NEXT_PUBLIC_DEMO=1 builds only). It replays what the real simulation API
// answered in library mode, recorded by demo/record/record_simulations.py into web/demo-data/: the library, each stored
// Environment, the Kit under /vendor/kit (next.config.mjs rewrites /vendor/* here), and the /ask stream of every question the
// library answers. No model is called. Each Environment's Content-Security-Policy names the origin its Kit is served from, which
// was http://localhost:3001 when it was recorded, so that origin is rewritten to the one serving this request, and the HTML's
// SHA-256 is computed again afterwards: the real server also injects the CSP at serve time and hashes the result, and the
// browser refuses any Environment whose HTML does not match its hash.

import { createHash } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ENABLED = process.env.NEXT_PUBLIC_DEMO === "1";
const DATA = path.join(process.cwd(), "demo-data");
const RECORDED_ORIGIN = "http://localhost:3001";

type Route = { status: number; file: string; type: string };
type AskEntry = { question: string; file: string };
type Frame = { t: number; data: string };

const cache = new Map<string, unknown>();
async function readJson<T>(rel: string): Promise<T> {
  if (!cache.has(rel)) cache.set(rel, JSON.parse(await fs.readFile(path.join(DATA, rel), "utf-8")));
  return cache.get(rel) as T;
}

/** Every Environment in a JSON value: its HTML moved to `origin`, and its hash computed again from the HTML it now carries. */
function rehome(value: unknown, origin: string): unknown {
  if (Array.isArray(value)) return value.map((v) => rehome(v, origin));
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) out[k] = rehome(v, origin);
    if (typeof out.html === "string" && typeof out.htmlSha256 === "string") {
      out.htmlSha256 = createHash("sha256").update(out.html, "utf8").digest("hex");
    }
    return out;
  }
  return typeof value === "string" ? value.split(RECORDED_ORIGIN).join(origin) : value;
}

/** A JSON text with every Environment re-homed; text that is not JSON gets the plain origin swap. */
function rehomeText(text: string, origin: string): string {
  try {
    return JSON.stringify(rehome(JSON.parse(text), origin));
  } catch {
    return text.split(RECORDED_ORIGIN).join(origin);
  }
}

/** A file's bytes as an ArrayBuffer, which every Response accepts. */
const bytes = (buf: Buffer): ArrayBuffer => buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength) as ArrayBuffer;

function originOf(request: Request): string {
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  const proto = request.headers.get("x-forwarded-proto") ?? new URL(request.url).protocol.replace(":", "");
  return host ? `${proto}://${host}` : new URL(request.url).origin;
}

const envelope = (code: string, message: string, status: number) =>
  new Response(JSON.stringify({ code, message, issues: [], retryable: false }), {
    status,
    headers: { "content-type": "application/json" },
  });

const STOP = new Set("a an the of on in for to and or is are what which how why who does do can i my me it its this that when with".split(" "));
const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9\s]/g, " ").replace(/\s+/g, " ").trim();
const words = (s: string) => new Set(norm(s).split(" ").filter((w) => w && !STOP.has(w)));

async function findAsk(question: string): Promise<AskEntry | null> {
  const index = await readJson<AskEntry[]>("ask/index.json");
  const exact = index.find((e) => norm(e.question) === norm(question));
  if (exact) return exact;
  const x = words(question);
  let best: AskEntry | null = null;
  let score = 0;
  for (const e of index) {
    const y = words(e.question);
    let both = 0;
    for (const w of x) if (y.has(w)) both++;
    const s = x.size && y.size ? both / (x.size + y.size - both) : 0;
    if (s > score) [best, score] = [e, s];
  }
  return score >= 0.6 ? best : null;
}

function sse(frames: Frame[], origin: string): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      let last = 0;
      for (const f of frames) {
        const wait = Math.min(Math.max(0, f.t - last) * 0.5, 700);
        last = f.t;
        if (wait > 0) await new Promise((r) => setTimeout(r, wait));
        const line = f.data.startsWith("data: ") ? `data: ${rehomeText(f.data.slice(6), origin)}` : f.data;
        controller.enqueue(encoder.encode(`${line}\n\n`));
      }
      controller.close();
    },
  });
  return new Response(stream, { headers: { "content-type": "text/event-stream", "cache-control": "no-cache, no-transform" } });
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(request: Request, ctx: Ctx): Promise<Response> {
  if (!ENABLED) return new Response("Not found", { status: 404 });
  const parts = (await ctx.params).path;

  if (parts[0] === "vendor" && parts[1] === "kit") {
    const rel = path.normalize(parts.slice(2).join("/"));
    if (rel.startsWith("..") || path.isAbsolute(rel)) return new Response("Not found", { status: 404 });
    try {
      const body = bytes(await fs.readFile(path.join(DATA, "vendor", "kit", rel)));
      const type = rel.endsWith(".js") ? "text/javascript" : rel.endsWith(".json") ? "application/json" : rel.endsWith(".woff2") ? "font/woff2" : "application/octet-stream";
      return new Response(body, {
        headers: { "content-type": type, "access-control-allow-origin": "*", "cache-control": "public, max-age=31536000, immutable" },
      });
    } catch {
      return new Response("Not found", { status: 404 });
    }
  }

  const key = `GET /${parts.map(encodeURIComponent).join("/")}`;
  const routes = await readJson<Record<string, Route>>("routes.json");
  const hit = routes[key];
  if (!hit) return envelope("not_found", "This is not part of the hosted demo's recording.", 404);
  const raw = await fs.readFile(path.join(DATA, hit.file));
  const isText = hit.type.includes("json") || hit.type.includes("html") || hit.type.includes("text");
  const body = isText ? rehomeText(raw.toString("utf-8"), originOf(request)) : bytes(raw);
  return new Response(body, { status: hit.status, headers: { "content-type": hit.type } });
}

export async function POST(request: Request, ctx: Ctx): Promise<Response> {
  if (!ENABLED) return new Response("Not found", { status: 404 });
  const parts = (await ctx.params).path;
  if (parts.length === 1 && parts[0] === "ask") {
    const body = (await request.json().catch(() => ({}))) as { question?: unknown };
    const question = typeof body.question === "string" ? body.question : "";
    if (!question.trim()) return envelope("bad_request", "The question is empty.", 400);
    const entry = await findAsk(question);
    if (!entry) {
      const index = await readJson<AskEntry[]>("ask/index.json");
      const error = {
        code: "not_found",
        message:
          "This hosted demo shows the simulations stored in the library, recorded from the real engine; it does not build new ones. " +
          `Try one of the quick starts, for example "${index[0]?.question ?? ""}". Run Synapse locally to have a simulation written for any question.`,
        issues: [],
        retryable: false,
      };
      return sse([{ t: 0, data: `data: ${JSON.stringify({ type: "error", error })}` }], originOf(request));
    }
    const recorded = await readJson<{ frames: Frame[] }>(entry.file);
    return sse(recorded.frames, originOf(request));
  }
  return envelope("bad_request", "The hosted demo is read-only: it replays recorded simulations and cannot change the library.", 400);
}
