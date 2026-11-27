"use client";

// The welcome carousel of the hosted demo: three slides on first visit, then the choice of a quick tour. Every colour is a design
// token (dark mode follows), the pictures draw themselves (globals.css intro-* keyframes, off under reduced motion), and the
// dialog keeps focus: Escape skips, Tab loops. Pattern from the onboarding guide (azimskill:onboarding).

import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";

import { Axi } from "@/components/shell/Axi";

type Slide = { title: string; text: string; picture: ReactNode };

const ink = "var(--color-stone-900)";
const soft = "var(--color-stone-400)";
const accent = "var(--color-accent)";

function GraphPicture() {
  const nodes = [
    [40, 50, 9],
    [120, 34, 7],
    [176, 86, 10],
    [92, 112, 8],
    [30, 128, 6],
  ] as const;
  const links = ["M40 50L120 34", "M40 50L92 112", "M120 34L176 86", "M92 112L176 86", "M30 128L92 112"];
  return (
    <svg viewBox="0 0 210 160" className="h-full w-full" aria-hidden>
      {links.map((d, i) => (
        <path key={d} d={d} pathLength={1} stroke={soft} strokeWidth={2.5} fill="none" className="intro-draw" style={{ animationDelay: `${i * 0.12}s` }} />
      ))}
      {nodes.map(([x, y, r], i) => (
        <circle key={i} cx={x} cy={y} r={r} fill={i === 2 ? accent : ink} className="intro-pop" style={{ animationDelay: `${0.5 + i * 0.08}s`, transformOrigin: `${x}px ${y}px` }} />
      ))}
      <g className="intro-rise" style={{ animationDelay: "1s" }}>
        <rect x={112} y={118} width={88} height={30} rx={8} fill="var(--color-white)" stroke={soft} />
        <rect x={120} y={127} width={52} height={4} rx={2} fill={ink} />
        <rect x={120} y={136} width={36} height={4} rx={2} fill={accent} />
      </g>
    </svg>
  );
}

function SimulationPicture() {
  return (
    <svg viewBox="0 0 210 160" className="h-full w-full" aria-hidden>
      <path d="M26 20H86" stroke={ink} strokeWidth={4} strokeLinecap="round" />
      <path d="M56 20V34l-12 6 24 8-24 8 24 8-24 8 12 6v10" pathLength={1} stroke={accent} strokeWidth={3} fill="none" className="intro-draw" />
      <rect x={42} y={92} width={28} height={22} rx={4} fill={ink} className="intro-pop" style={{ animationDelay: "0.9s", transformOrigin: "56px 103px" }} />
      <path d="M112 128H196M112 128V30" stroke={soft} strokeWidth={2} />
      <path d="M112 128L190 44" pathLength={1} stroke={accent} strokeWidth={3} fill="none" className="intro-draw" style={{ animationDelay: "0.5s" }} />
      {[
        [131, 108],
        [151, 86],
        [171, 65],
      ].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={5} fill={ink} className="intro-pop" style={{ animationDelay: `${1.1 + i * 0.15}s`, transformOrigin: `${x}px ${y}px` }} />
      ))}
    </svg>
  );
}

function ReplayPicture() {
  return (
    <svg viewBox="0 0 210 160" className="h-full w-full" aria-hidden>
      {[0, 1, 2].map((i) => (
        <g key={i} className="intro-rise" style={{ animationDelay: `${0.15 + i * 0.18}s` }}>
          <rect x={30} y={28 + i * 38} width={150} height={28} rx={14} fill="var(--color-white)" stroke={soft} />
          <rect x={46} y={39 + i * 38} width={i === 1 ? 70 : 96} height={6} rx={3} fill={i === 0 ? accent : ink} />
        </g>
      ))}
      <circle cx={166} cy={132} r={18} fill={ink} className="intro-pop" style={{ animationDelay: "0.9s", transformOrigin: "166px 132px" }} />
      <path d="M161 123l12 9-12 9z" fill="var(--color-stone-50)" className="intro-pop" style={{ animationDelay: "1s", transformOrigin: "166px 132px" }} />
    </svg>
  );
}

export const SLIDES: Slide[] = [
  {
    title: "Ask the papers, check every answer",
    text: "Synapse reads a set of documents into one knowledge graph. Each sentence of an answer quotes the paper and page it came from, and a question the papers do not cover gets “not found”, never a guess.",
    picture: <GraphPicture />,
  },
  {
    title: "See an idea move",
    text: "Press Simulate and a question becomes a hands-on simulation you drag and drop, tested in a real browser before you can touch it.",
    picture: <SimulationPicture />,
  },
  {
    title: "You are in the hosted demo",
    text: "Everything here was recorded from the real system on 16 sample research papers about retrieval and knowledge graphs. Try the suggested questions, any Studio tool and the simulations. In your own copy you can delete the samples and add your own documents.",
    picture: <ReplayPicture />,
  },
];

export function Intro({ onTour, onSkip }: { onTour: () => void; onSkip: () => void }) {
  const [index, setIndex] = useState(0);
  const [dir, setDir] = useState<"next" | "back">("next");
  const panel = useRef<HTMLDivElement>(null);
  const last = index === SLIDES.length - 1;
  const slide = SLIDES[index] ?? SLIDES[0]!;

  useEffect(() => panel.current?.focus(), [index]);

  const go = (to: number) => {
    setDir(to > index ? "next" : "back");
    setIndex(to);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      onSkip();
      return;
    }
    if (e.key !== "Tab" || !panel.current) return;
    const items = [...panel.current.querySelectorAll<HTMLElement>("button:not([disabled]), [href]")];
    const first = items[0];
    const end = items[items.length - 1];
    if (!first || !end) return;
    if (e.shiftKey && (document.activeElement === first || document.activeElement === panel.current)) {
      e.preventDefault();
      end.focus();
    } else if (!e.shiftKey && document.activeElement === end) {
      e.preventDefault();
      first.focus();
    }
  };

  return (
    <div className="fixed inset-0 z-[60] grid place-items-center bg-[rgba(12,11,9,0.62)] p-4 backdrop-blur-[2px]">
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-label="Welcome to Synapse"
        tabIndex={-1}
        onKeyDown={onKeyDown}
        className="grid w-full max-w-3xl overflow-hidden rounded-3xl bg-stone-50 shadow-[0_24px_64px_rgba(0,0,0,0.3)] outline-none sm:grid-cols-[0.9fr_1.1fr]"
      >
        <div className="flex flex-col gap-4 bg-stone-900 p-6 text-stone-50">
          <div className="flex items-center gap-2">
            <Axi size={32} />
            <span className="font-display text-xl font-semibold">Synapse</span>
          </div>
          <div key={index} data-intro-card className={`ob-in-${dir} aspect-[5/4] rounded-2xl bg-stone-50 p-3 sm:aspect-square`}>
            {slide.picture}
          </div>
        </div>

        <div className="flex min-h-[23rem] flex-col p-6">
          <div className="flex items-center gap-3">
            <div className="flex flex-1 gap-1.5" aria-hidden>
              {SLIDES.map((s, i) => (
                <span key={s.title} className={`h-1 flex-1 rounded-full ${i <= index ? "bg-accent" : "bg-stone-200"}`} />
              ))}
            </div>
            <button type="button" onClick={onSkip} className="text-sm text-stone-500 hover:text-stone-900">
              Skip
            </button>
          </div>
          <div key={index} className={`ob-in-${dir} mt-6 flex-1`}>
            <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">
              Step {index + 1} of {SLIDES.length}
            </p>
            <h2 className="mt-2 min-h-[3.75em] font-display text-2xl font-semibold leading-tight text-stone-900 sm:min-h-[2.5em]">{slide.title}</h2>
            <p className="mt-2 min-h-[11.4em] text-[15px] sm:min-h-[8.2em] leading-relaxed text-stone-600">{slide.text}</p>
          </div>
          <div className="mt-4 flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={() => go(index - 1)}
              disabled={index === 0}
              className="rounded-xl px-1 py-2 text-sm text-stone-600 hover:text-stone-900 disabled:invisible sm:px-3"
            >
              Back
            </button>
            {last ? (
              <div className="flex gap-2">
                <button type="button" onClick={onSkip} className="whitespace-nowrap rounded-xl border border-stone-300 px-3 py-2 text-sm text-stone-700 hover:border-stone-500">
                  Skip the tour
                </button>
                <button type="button" onClick={onTour} className="whitespace-nowrap rounded-xl bg-stone-900 px-3 py-2 text-sm font-medium text-stone-50 sm:px-4">
                  Take a quick tour
                </button>
              </div>
            ) : (
              <button type="button" onClick={() => go(index + 1)} className="rounded-xl bg-stone-900 px-4 py-2 text-sm font-medium text-stone-50">
                Next
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
