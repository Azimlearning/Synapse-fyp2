"use client";

// Simulations in the chat: the generative UI side of Synapse. "Simulate" in the main question box (or a prebuilt question from the
// picker) turns a question into an interactive Environment, built by the simulation engine (genui/: its own API, browser verifier
// and sandbox host) and checked in a real browser before it can be used. It runs INSIDE the chat as a card that holds only the
// simulation; the short note the engine writes sits above it as an ordinary chat message. The engine is a different origin, so it
// can never read this page; it tells the card only which Environment is ready (id, title, note), and is told the colour mode.

import { useEffect, useRef, useState } from "react";

import { Axi } from "@/components/shell/Axi";
import { readTheme, SIMULATIONS_ORIGIN, SIMULATIONS_URL, type UiTheme } from "@/lib/theme";

/** Prebuilt simulations: questions the engine has stored, verified, and answers at once with no model call (each question word for word as it is
 *  remembered in genui/data/environments.db). General science first (the Kit-verified ones built from audited parts, then model-written ones checked in
 *  a real browser), then three built from the topics of the uploaded papers (retrieval-augmented generation). */
export const PREBUILT_SIMULATIONS: { question: string; topic: string; group: "science" | "papers" }[] = [
  { question: "Why does a spring stretch when I hang a weight on it?", topic: "Hooke's law", group: "science" },
  { question: "What happens to the current if I raise the resistance in a circuit?", topic: "Ohm's law", group: "science" },
  { question: "How does the pressure change as a diver goes deeper in water?", topic: "Pressure in a liquid", group: "science" },
  { question: "How much would I weigh on Jupiter compared with Earth?", topic: "Gravity on the planets", group: "science" },
  { question: "How does a black hole bend light?", topic: "Black hole bending light", group: "science" },
  { question: "How does the length of a pendulum change how long each swing takes?", topic: "Pendulum", group: "science" },
  {
    question: "How does reciprocal rank fusion merge a keyword search ranking and a vector search ranking into one list?",
    topic: "Hybrid search: reciprocal rank fusion",
    group: "papers",
  },
  { question: "How does the size of a text chunk change whether retrieval finds the right passage?", topic: "Chunk size and retrieval", group: "papers" },
  {
    question: "How does following links in a knowledge graph find an answer that is two hops away from the question?",
    topic: "Multi-hop search in a knowledge graph",
    group: "papers",
  },
];

const GROUPS: { id: "science" | "papers"; title: string; aside: string }[] = [
  { id: "science", title: "General science", aside: "drag, drop and turn by hand" },
  { id: "papers", title: "From your papers", aside: "retrieval and knowledge graphs" },
];

export interface ReadySimulation {
  envId: string;
  title: string;
  question: string;
  note: string;
  /** What the Environment earned (genui's trust label, e.g. kit-verified, model-checked), shown beside it. */
  label?: string;
}

/** Where a simulation is shown: a new one built from a question, or a stored one by id (the simulation alone). */
export function simulationSrc(request: { question?: string | null; envId?: string | null }, theme: UiTheme): string {
  if (request.envId) return `${SIMULATIONS_URL}/e/${encodeURIComponent(request.envId)}?embed=1&theme=${theme}`;
  return `${SIMULATIONS_URL}/?embed=1&theme=${theme}${request.question ? `&q=${encodeURIComponent(request.question)}` : ""}`;
}

/** A simulation in the chat. With `question` the engine builds it (showing its progress) and `onReady` reports the finished
 *  Environment; with `envId` it shows a finished one, the simulation alone. */
export function SimulationCard({
  envId,
  question,
  title,
  label,
  onReady,
}: {
  envId?: string | null;
  question?: string | null;
  title: string;
  /** The stored simulation's trust label, when it is shown again from the chat history. */
  label?: string;
  onReady?: (sim: ReadySimulation) => void;
}) {
  const [theme, setTheme] = useState<UiTheme>("light");
  const [parts, setParts] = useState<SimParts | null>(null);
  // Once the engine reports the finished Environment, the box shows that Environment alone (its bench), not the build page around it.
  const [ready, setReady] = useState<{ id: string; label: string; lane: string } | null>(null);
  const frame = useRef<HTMLIFrameElement | null>(null);
  // eslint-disable-next-line react-hooks/set-state-in-effect -- the colour mode is only known in the browser
  useEffect(() => setTheme(readTheme()), []);
  useEffect(() => {
    const onMessage = (e: MessageEvent) => {
      if (e.origin !== SIMULATIONS_ORIGIN || e.source !== frame.current?.contentWindow) return;
      const d = e.data as
        | { type?: unknown; id?: unknown; title?: unknown; question?: unknown; note?: unknown; parts?: unknown; label?: unknown; lane?: unknown }
        | null;
      // The words and questions of the simulation (the frame shows only its bench): drawn here, outside it.
      if (d?.type === "synapse_env_parts") {
        setParts(readParts(d.parts));
        return;
      }
      if (d?.type === "synapse_environment" && typeof d.id === "string" && typeof d.title === "string") {
        setReady({ id: d.id, label: typeof d.label === "string" ? d.label : "", lane: typeof d.lane === "string" ? d.lane : "" });
      }
      if (onReady && d?.type === "synapse_environment" && typeof d.id === "string" && typeof d.title === "string") {
        onReady({
          envId: d.id,
          title: d.title,
          question: typeof d.question === "string" ? d.question : d.title,
          note: typeof d.note === "string" ? d.note : "",
          label: typeof d.label === "string" ? d.label : undefined,
        });
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [onReady]);

  const shownId = envId ?? ready?.id ?? null;
  const building = !shownId;
  const hasQuiz = parts !== null && (parts.predicts.length > 0 || parts.checks.length > 0);
  const shownLabel = ready?.label || label || "";
  const earned = shownLabel ? LABEL_WORDS[shownLabel] ?? shownLabel : null;
  return (
    <div className="space-y-3">
      {parts && <SimTextBox parts={parts} />}
      <div className="overflow-hidden rounded-2xl bg-white shadow-[0_1px_2px_rgba(35,33,28,0.06),0_0_0_1px_var(--color-stone-200)]">
        <div className="flex items-center gap-2 border-b border-stone-200 px-4 py-2">
          <Axi size={24} mood={building ? "thinking" : "happy"} bob={building} />
          <p className="min-w-0 flex-1 truncate text-sm">
            <span className="nb-label mr-2">Simulation</span>
            <span className="font-medium text-stone-900">{parts?.title ?? title}</span>
            {building && <span className="ml-2 font-serif text-xs italic text-stone-500">building and checking in a real browser…</span>}
          </p>
          {earned && (
            <span
              title={
                shownLabel === "model-checked"
                  ? "Written by a model for this question, then checked in a real browser"
                  : "Built from audited Kit parts, then checked in a real browser"
              }
              className="shrink-0 rounded-full border border-[#3d7a52] bg-[#eaf3ec] px-2 py-0.5 text-xs text-[#23211c]"
            >
              {earned}
            </span>
          )}
        </div>
        {/* The simulation fills this box: while it is being built, the engine's progress; once ready, the Environment's bench alone. */}
        <iframe
          key={shownId ?? "building"}
          ref={frame}
          data-simulations
          title={`Simulation: ${title}`}
          src={simulationSrc({ envId: shownId, question }, theme)}
          className="h-[min(620px,72vh)] w-full border-0 bg-stone-50"
          allow="clipboard-write; fullscreen"
        />
      </div>
      {hasQuiz && <SimQuizBox parts={parts} />}
    </div>
  );
}

/** What each verification label means in a few words (the engine's lanes and labels, genui V5-D03): shown beside the simulation, outside it. */
const LABEL_WORDS: Record<string, string> = {
  "source-verified": "Source verified",
  "kit-verified": "Kit verified",
  "model-checked": "Model-checked",
  "browser-checked": "Browser-checked",
};

// ── The words and questions of a simulation, shown outside it ────────────────────────────────────────────────────────────────

export interface SimParts {
  kicker?: string;
  title?: string;
  tryThis?: string;
  keyIdea?: string;
  steps: string[];
  hints: string[];
  texts: string[];
  experiment?: { aim?: string; hypothesis?: string; independent?: string; dependent?: string; controlled?: string[]; apparatus?: string[] };
  predicts: { prompt: string; choices: string[]; reveal: string }[];
  checks: { question: string; options: string[]; correct: number; explanation: string }[];
}

const txt = (v: unknown): string | undefined => (typeof v === "string" && v.trim() ? v : undefined);
const txts = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === "string" && x.trim() !== "") : []);

/** The engine's message, re-read field by field: only strings and lists of strings are kept (it is rendered as text, never as markup). */
function readParts(raw: unknown): SimParts | null {
  if (raw === null || typeof raw !== "object") return null;
  const r = raw as Record<string, unknown>;
  const exp = r.experiment as Record<string, unknown> | undefined;
  return {
    kicker: txt(r.kicker),
    title: txt(r.title),
    tryThis: txt(r.tryThis),
    keyIdea: txt(r.keyIdea),
    steps: txts(r.steps),
    hints: txts(r.hints),
    texts: txts(r.texts),
    experiment:
      exp && typeof exp === "object"
        ? { aim: txt(exp.aim), hypothesis: txt(exp.hypothesis), independent: txt(exp.independent), dependent: txt(exp.dependent), controlled: txts(exp.controlled), apparatus: txts(exp.apparatus) }
        : undefined,
    predicts: (Array.isArray(r.predicts) ? r.predicts : []).flatMap((p) => {
      const o = p as Record<string, unknown>;
      const prompt = txt(o?.prompt);
      const choices = txts(o?.choices);
      return prompt && choices.length > 1 ? [{ prompt, choices, reveal: txt(o.reveal) ?? "" }] : [];
    }),
    checks: (Array.isArray(r.checks) ? r.checks : []).flatMap((c) => {
      const o = c as Record<string, unknown>;
      const question = txt(o?.question);
      const options = txts(o?.options);
      const correct = typeof o?.correct === "number" ? o.correct : -1;
      return question && options.length > 1 && correct >= 0 && correct < options.length
        ? [{ question, options, correct, explanation: txt(o.explanation) ?? "" }]
        : [];
    }),
  };
}

const BOX = "rounded-2xl bg-white p-4 shadow-[0_1px_2px_rgba(35,33,28,0.06),0_0_0_1px_var(--color-stone-200)]";

/** The simulation's heading, aim, steps and hints, as an ordinary chat text box. */
function SimTextBox({ parts }: { parts: SimParts }) {
  const exp = parts.experiment;
  return (
    <div className={`${BOX} space-y-2`}>
      {parts.title && <p className="font-display text-lg font-semibold text-stone-900">{parts.title}</p>}
      {parts.tryThis && (
        <p className="text-sm text-stone-800">
          <span className="font-semibold">Try this:</span> {parts.tryThis}
        </p>
      )}
      {parts.keyIdea && (
        <p className="rounded-lg bg-stone-100 px-3 py-2 text-sm text-stone-800">
          <span className="font-semibold">Key idea:</span> {parts.keyIdea}
        </p>
      )}
      {exp?.aim && (
        <p className="text-sm text-stone-700">
          <span className="font-semibold">Aim:</span> {exp.aim}
          {exp.independent && exp.dependent && (
            <span className="text-stone-500">
              {" "}
              (change {exp.independent.toLowerCase()}, measure {exp.dependent.toLowerCase()})
            </span>
          )}
        </p>
      )}
      {parts.steps.length > 0 && (
        <ol className="list-decimal space-y-0.5 pl-5 text-sm text-stone-700">
          {parts.steps.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ol>
      )}
      {parts.hints.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer text-stone-600 hover:text-stone-900">Need a hint?</summary>
          <ol className="mt-1 list-decimal space-y-0.5 pl-5 text-stone-700">
            {parts.hints.map((h) => (
              <li key={h}>{h}</li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}

/** The simulation's questions as a quiz box: a prediction to make before trying (its answer revealed on choosing), and checks
 *  marked right or wrong with the explanation. Nothing is stored or sent: it is the learner's own practice. */
function SimQuizBox({ parts }: { parts: SimParts }) {
  const [picked, setPicked] = useState<Record<string, number>>({});
  const choose = (key: string, i: number) => setPicked((p) => (key in p ? p : { ...p, [key]: i }));
  return (
    <section aria-label="Quiz" className={`${BOX} space-y-4`}>
      <p className="nb-label">
        Quiz<span className="nb-aside">from this simulation</span>
      </p>
      {parts.predicts.map((p, n) => {
        const key = `p${n}`;
        const chosen = picked[key];
        return (
          <div key={key} className="space-y-2">
            <p className="text-sm font-medium text-stone-900">
              <span className="mr-1.5 text-xs uppercase tracking-wide text-stone-500">Predict</span>
              {p.prompt}
            </p>
            <div className="flex flex-wrap gap-2">
              {p.choices.map((c, i) => (
                <button
                  key={c}
                  type="button"
                  disabled={chosen !== undefined}
                  onClick={() => choose(key, i)}
                  className={`rounded-xl border px-3 py-1.5 text-sm ${chosen === i ? "border-stone-900 bg-stone-900 text-white" : "border-stone-300 bg-white text-stone-800 hover:border-stone-500"} disabled:cursor-default`}
                >
                  {c}
                </button>
              ))}
            </div>
            {chosen !== undefined && p.reveal && (
              <p role="status" className="rounded-lg bg-stone-100 px-3 py-2 text-sm text-stone-700">
                Now try it in the simulation. {p.reveal}
              </p>
            )}
          </div>
        );
      })}
      {parts.checks.map((c, n) => {
        const key = `c${n}`;
        const chosen = picked[key];
        const right = chosen === c.correct;
        return (
          <div key={key} className="space-y-2">
            <p className="text-sm font-medium text-stone-900">{c.question}</p>
            <div className="flex flex-wrap gap-2">
              {c.options.map((o, i) => (
                <button
                  key={o}
                  type="button"
                  disabled={chosen !== undefined}
                  onClick={() => choose(key, i)}
                  className={`rounded-xl border px-3 py-1.5 text-sm disabled:cursor-default ${
                    chosen === undefined
                      ? "border-stone-300 bg-white text-stone-800 hover:border-stone-500"
                      : i === c.correct
                        ? "border-[#3d7a52] bg-[#eaf3ec] text-[#23211c]"
                        : i === chosen
                          ? "border-[#a8423a] bg-[#f7e8e6] text-[#23211c]"
                          : "border-stone-200 bg-white text-stone-500"
                  }`}
                >
                  {o}
                  {chosen !== undefined && i === c.correct ? " (the answer)" : ""}
                </button>
              ))}
            </div>
            {chosen !== undefined && (
              <p role="status" className="text-sm text-stone-700">
                <span className="font-semibold">{right ? "Correct." : "Not quite."}</span> {c.explanation}
              </p>
            )}
          </div>
        );
      })}
    </section>
  );
}

export type DrawerRequest = { kind: "picker" } | { kind: "view"; envId: string; title: string };

/** The drawer: the prebuilt simulations to pick from (a pick runs in the chat), or one simulation shown large. */
export function SimulationDrawer({
  request,
  onClose,
  onPick,
}: {
  request: DrawerRequest | null;
  onClose: () => void;
  onPick: (question: string) => void;
}) {
  const [theme, setTheme] = useState<UiTheme>("light");
  // eslint-disable-next-line react-hooks/set-state-in-effect -- the colour mode is only known in the browser
  useEffect(() => setTheme(readTheme()), [request]);
  useEffect(() => {
    if (!request) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [request, onClose]);

  if (!request) return null;
  const large = request.kind === "view";
  return (
    <div className="fixed inset-0 z-40 flex justify-end" role="dialog" aria-modal="true" aria-label="Simulations">
      <button type="button" aria-label="Close" onClick={onClose} className="absolute inset-0 bg-stone-950/25" />
      <div
        className={`relative flex h-full flex-col border-l border-stone-200 bg-stone-50 shadow-[0_0_40px_rgba(35,33,28,0.18)] max-md:w-full ${
          large ? "w-[min(1180px,80vw)]" : "w-[min(520px,92vw)]"
        }`}
      >
        <div className="flex items-center gap-3 border-b border-stone-200 px-4 py-2.5">
          <Axi size={34} bob />
          <div className="min-w-0 flex-1">
            <p className="font-display text-lg font-semibold leading-tight text-stone-900">{large ? request.title : "Simulations"}</p>
            <p className="truncate font-serif text-xs italic text-stone-500">
              {large ? "The simulation from your chat" : "Pick one: it runs in your chat. Or press Simulate beside Ask for your own question."}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-stone-300 bg-white px-3 py-1 text-xs text-stone-600 hover:text-stone-900"
          >
            Close
          </button>
        </div>
        {large ? (
          <iframe
            data-simulations
            title={`Simulation: ${request.title}`}
            src={simulationSrc({ envId: request.envId }, theme)}
            className="min-h-0 w-full flex-1 border-0 bg-stone-50"
            allow="clipboard-write; fullscreen"
          />
        ) : (
          <div className="space-y-4 overflow-y-auto p-4">
            {GROUPS.map((g) => (
              <section key={g.id} aria-label={g.title} className="space-y-2">
                <h3 className="nb-label">
                  {g.title}
                  <span className="nb-aside">{g.aside}</span>
                </h3>
                <ul className="space-y-2">
                  {PREBUILT_SIMULATIONS.filter((s) => s.group === g.id).map((s) => (
                    <li key={s.question}>
                      <button
                        type="button"
                        onClick={() => onPick(s.question)}
                        className="flex w-full items-start gap-3 rounded-xl bg-white p-3 text-left shadow-[0_0_0_1px_var(--color-stone-200)] transition hover:-translate-y-px hover:shadow-[0_6px_16px_rgba(35,33,28,0.10),0_0_0_1px_var(--color-stone-300)]"
                      >
                        <Axi size={30} />
                        <span className="min-w-0">
                          <span className="block text-sm font-medium text-stone-900">{s.topic}</span>
                          <span className="block font-serif text-sm italic text-stone-600">{s.question}</span>
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
            <p className="px-1 font-serif text-xs italic text-stone-500">
              Each is a simulation already built and checked in a real browser, ready at once. A new question is built and checked first, which
              takes a few minutes.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

/** The corner button: Axi, opening the prebuilt simulations. */
export function SimulationLauncher({ onOpen }: { onOpen: () => void }) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="fixed bottom-5 right-5 z-30 flex items-center gap-2 rounded-full bg-white py-1.5 pl-1.5 pr-4 text-sm font-medium text-stone-800 shadow-[0_6px_20px_rgba(35,33,28,0.16),0_0_0_1px_var(--color-stone-200)] hover:shadow-[0_8px_24px_rgba(35,33,28,0.22),0_0_0_1px_var(--color-stone-300)]"
      title="Prebuilt, browser-verified simulations"
    >
      <Axi size={36} bob />
      Simulations
    </button>
  );
}
