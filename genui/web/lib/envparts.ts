// The parts of an Environment that are words, not apparatus: its heading (kicker, title, "Try this", key idea), the steps, the hints,
// the experiment card, and its questions (predict cards and concept checks). Inside the Synapse workspace these are shown by the
// workspace's chat as a text box and a quiz box, and the framed Environment shows only its bench.
//
// They are READ from the Environment's HTML as text, after the browser has re-hashed it (hard constraint 1): each Kit call's options
// are literal JSON-like objects written by the server's assembler, so they are found by name and parsed with JSON.parse (unquoted keys
// are quoted first). Nothing in the HTML is executed here, and a part that does not parse is simply left out.

export interface PredictPart {
  prompt: string;
  choices: string[];
  reveal: string;
}
export interface CheckPart {
  question: string;
  options: string[];
  correct: number;
  explanation: string;
}
export interface ExperimentPart {
  aim?: string;
  hypothesis?: string;
  independent?: string;
  dependent?: string;
  controlled?: string[];
  apparatus?: string[];
}
export interface EnvParts {
  kicker?: string;
  title?: string;
  tryThis?: string;
  keyIdea?: string;
  steps: string[];
  hints: string[];
  texts: string[];
  experiment?: ExperimentPart;
  predicts: PredictPart[];
  checks: CheckPart[];
}

/** The text of the balanced `{...}` (or a string literal) starting at `start`, or null. Quotes and escapes are respected. */
function literalAt(src: string, start: number): string | null {
  const open = src[start];
  if (open === '"') {
    for (let i = start + 1; i < src.length; i++) {
      if (src[i] === "\\") i++;
      else if (src[i] === '"') return src.slice(start, i + 1);
    }
    return null;
  }
  if (open !== "{") return null;
  let depth = 0;
  let inString = false;
  for (let i = start; i < src.length; i++) {
    const ch = src[i];
    if (inString) {
      if (ch === "\\") i++;
      else if (ch === '"') inString = false;
      continue;
    }
    if (ch === '"') inString = true;
    else if (ch === "{") depth++;
    else if (ch === "}" && --depth === 0) return src.slice(start, i + 1);
  }
  return null;
}

function parseLiteral(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    // Object literals written with bare keys ({ title: "..." }): quote the keys that are outside strings, then parse.
    let out = "";
    let inString = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (inString) {
        out += ch;
        if (ch === "\\") out += text[++i] ?? "";
        else if (ch === '"') inString = false;
        continue;
      }
      if (ch === '"') {
        inString = true;
        out += ch;
        continue;
      }
      const key = /^[A-Za-z_]\w*(?=\s*:)/.exec(text.slice(i));
      if (key && /[{,\s]$/.test(out)) {
        out += `"${key[0]}"`;
        i += key[0].length - 1;
        continue;
      }
      out += ch;
    }
    try {
      return JSON.parse(out);
    } catch {
      return null;
    }
  }
}

/** Every options literal passed to `Synapse.<name>(` in the HTML (the first argument when it is not `env`, else the second). */
function callsOf(html: string, name: string): unknown[] {
  const found: unknown[] = [];
  const re = new RegExp(`Synapse\\.${name}\\(\\s*(?:env\\s*,\\s*)?`, "g");
  let m: RegExpExecArray | null;
  while ((m = re.exec(html)) !== null) {
    const lit = literalAt(html, m.index + m[0].length);
    if (lit !== null) {
      const value = parseLiteral(lit);
      if (value !== null) found.push(value);
    }
  }
  return found;
}

const str = (v: unknown): string | undefined => (typeof v === "string" && v.trim() ? v : undefined);
const strs = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === "string" && x.trim() !== "") : []);

/** The words of a Free-lane page, read from the house frame's fixed markup (api/pipeline/free_house.py: header, key idea, predict, steps,
 *  hints, explanation). The HTML is parsed by DOMParser into an inert document (no script runs, nothing loads) and only text is kept. */
function houseParts(html: string): EnvParts | null {
  if (typeof DOMParser === "undefined" || !/<main class="lab"/.test(html)) return null;
  const doc = new DOMParser().parseFromString(html, "text/html");
  const text = (sel: string) => doc.querySelector(sel)?.textContent?.trim() || undefined;
  const all = (sel: string) => Array.from(doc.querySelectorAll(sel), (n) => n.textContent?.trim() ?? "").filter((t) => t !== "");
  const tryThis = doc.querySelector("main.lab .try")?.textContent?.replace(/^\s*Try this:\s*/i, "").trim() || undefined;
  const parts: EnvParts = {
    kicker: text("main.lab .kicker"),
    title: text("main.lab h1"),
    tryThis,
    keyIdea: all("main.lab .idea p").join(" ") || undefined,
    steps: all("main.lab .steps li"),
    hints: all("main.lab .hints details p"),
    texts: all("main.lab .explain p"),
    predicts: [],
    checks: [],
  };
  const predict = doc.querySelector("main.lab .predict");
  if (predict) {
    const prompt = predict.querySelector(":scope > p")?.textContent?.trim();
    const choices = Array.from(predict.querySelectorAll("ul li"), (n) => n.textContent?.trim() ?? "").filter((t) => t !== "");
    const reveal = predict.querySelector("details p")?.textContent?.trim() ?? "";
    if (prompt && choices.length > 1) parts.predicts.push({ prompt, choices, reveal });
  }
  return parts;
}

export function envParts(html: string): EnvParts {
  if (!/Synapse\.environment\(/.test(html)) {
    const house = houseParts(html);
    if (house) return house;
  }
  const head = (callsOf(html, "environment")[0] ?? {}) as Record<string, unknown>;
  const parts: EnvParts = {
    kicker: str(head.kicker),
    title: str(head.title),
    tryThis: str(head.tryThis),
    keyIdea: str(head.note),
    steps: callsOf(html, "stepper").flatMap((o) => strs((o as Record<string, unknown>)?.steps)),
    hints: callsOf(html, "hintLadder").flatMap((o) => strs((o as Record<string, unknown>)?.hints)),
    texts: callsOf(html, "text").filter((t): t is string => typeof t === "string" && t.trim() !== ""),
    predicts: [],
    checks: [],
  };
  for (const o of callsOf(html, "predictCard")) {
    const r = o as Record<string, unknown>;
    const prompt = str(r?.prompt);
    const choices = strs(r?.choices);
    if (prompt && choices.length > 1) parts.predicts.push({ prompt, choices, reveal: str(r.reveal) ?? "" });
  }
  for (const o of callsOf(html, "conceptCheck")) {
    const r = o as Record<string, unknown>;
    const question = str(r?.question);
    const options = strs(r?.options);
    const correct = typeof r?.correct === "number" ? r.correct : -1;
    if (question && options.length > 1 && correct >= 0 && correct < options.length) {
      parts.checks.push({ question, options, correct, explanation: str(r.explanation) ?? "" });
    }
  }
  const exp = callsOf(html, "experiment")[0] as Record<string, unknown> | undefined;
  if (exp) {
    parts.experiment = {
      aim: str(exp.aim),
      hypothesis: str(exp.hypothesis),
      independent: str(exp.independent),
      dependent: str(exp.dependent),
      controlled: strs(exp.controlled),
      apparatus: strs(exp.apparatus),
    };
  }
  return parts;
}

/** The stylesheet added to an embedded Environment (after its hash is checked): it hides the parts the workspace shows itself, so
 *  the frame holds only the bench, and lets the bench FILL the frame: the drawing takes the frame's height and most of its width, the
 *  controls, readouts and graph sit in a column beside it that scrolls on its own, and the page itself never scrolls (2026-11-24, the
 *  owner: the simulation should use the whole box, worked by hand). It covers both page shapes: the Kit's (`.syn-env`) and the
 *  model-written house frame of the Free lane (`main.lab`). Display only: no script is added, and the Environment's CSP allows inline
 *  styles. Below 560 px wide the columns stack and the page scrolls, as before. */
const BENCH_FILL = [
  // Kit pages: words and questions are shown by the workspace, outside the frame.
  ".syn-head,.syn-extras{display:none!important}",
  ".syn-env{max-width:none!important;padding:6px!important}",
  // Free-lane pages: the same.
  "main.lab>header,main.lab>.top,main.lab>.steps,main.lab>.hints,main.lab>.explain{display:none!important}",
  "main.lab{max-width:none!important;padding:6px!important}",
  "@media (min-width:560px){",
  "html,body{height:100%;overflow:hidden}",
  ".syn-env{height:100vh;grid-template-rows:minmax(0,1fr);gap:0!important}",
  ".syn-main{height:100%;min-height:0;grid-template-columns:minmax(0,2.2fr) minmax(230px,1fr)!important;align-items:stretch!important;gap:8px!important}",
  // Centred with flex and auto margins: the Kit's self-audit refuses any stylesheet with `content:` in it, and that includes the
  // `-content:` of align-content and justify-content (packages/kit/src/audit.ts, STYLE_FORBIDDEN), so neither is used here.
  ".syn-stage{height:100%;min-height:0;overflow:hidden;padding:8px!important;display:flex!important;flex-direction:column}",
  ".syn-stage>:first-child{margin-top:auto}.syn-stage>:last-child{margin-bottom:auto}",
  ".syn-stage .syn-scene{max-height:calc(100vh - 44px)!important}",
  ".syn-masses{height:100%;min-height:0;width:100%}",
  ".syn-masses>.syn-scene{max-height:calc(100vh - 170px)!important;height:100%}",
  // The Kit lays apparatus out in columns of at least 118 px, which leaves two parts small with empty columns beside them: here each
  // part gets a column of at least 200 px, so two parts share the bench and each is drawn large.
  ".syn-app-bench{flex:1 1 auto;min-height:0;width:100%;align-items:center!important;grid-template-columns:repeat(auto-fit,minmax(200px,1fr))!important}",
  ".syn-app{min-height:0}",
  ".syn-app-svg{width:100%;height:auto;max-width:none!important;max-height:calc(100vh - 200px)!important}",
  ".syn-panel{height:100%;min-height:0;overflow-y:auto;padding-right:2px}",
  ".syn-graph{max-height:190px}",
  "main.lab{height:100vh;grid-template-rows:minmax(0,1fr);gap:0!important}",
  "main.lab>.benchrow{height:100%;min-height:0;grid-template-columns:minmax(0,2.2fr) minmax(230px,1fr)!important;gap:8px!important}",
  "main.lab .bench{height:100%;min-height:0;display:flex;align-items:center}",
  "main.lab .bench svg{width:100%;height:100%!important;max-height:none!important}",
  "main.lab .side{height:100%;min-height:0;overflow-y:auto}",
  "}",
].join("");

export const EMBED_BENCH_ONLY_STYLE = `<style data-synapse-embed>${BENCH_FILL}</style>`;
