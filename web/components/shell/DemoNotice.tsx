"use client";

// The hosted demo (NEXT_PUBLIC_DEMO=1): a small fixed badge that says what the visitor is looking at, and the questions on the
// welcome card that have recorded answers. Neither is drawn in a normal build.

import { useState } from "react";

import { replayIntro } from "@/lib/introTour";

export const DEMO = process.env.NEXT_PUBLIC_DEMO === "1";
const REPO = "https://github.com/Azimlearning/Synapse-fyp2";
const SHOWCASE = "https://github.com/Azimlearning/Arcana-Final-Year-Project-UTP";

/** Questions with recorded answers (demo/record/record_graphrag.py CHAT). Each shows a different part of the system. */
export const DEMO_QUESTIONS: { label: string; question: string }[] = [
  { label: "Compare three systems", question: "How do GraphRAG, LightRAG and HippoRAG compare in how they use a knowledge graph for retrieval?" },
  { label: "Explain a method", question: "What is reciprocal rank fusion and how does HybridRAG combine graph and vector retrieval?" },
  { label: "Across all papers", question: "What failure modes of vector-only retrieval are identified across the papers?" },
  { label: "Multi-hop", question: "What is multi-hop question answering, and why is it hard for vector-only retrieval?" },
  { label: "Evaluation", question: "How is retrieval-augmented generation evaluated, and what does RAGAS measure?" },
  { label: "Not in the papers", question: "Who won the 2022 FIFA World Cup?" },
];

export function DemoBadge() {
  const [open, setOpen] = useState(false);
  if (!DEMO) return null;
  return (
    <div className="fixed bottom-3 left-3 z-50 max-w-xs text-xs">
      {open && (
        <div className="mb-2 rounded-xl bg-white p-3 leading-relaxed text-stone-600 shadow-[0_8px_24px_rgba(35,33,28,0.12),0_0_0_1px_var(--color-stone-200)]">
          <p className="font-semibold text-stone-900">Synapse, hosted demo</p>
          <p className="mt-1">
            Answers, Studio tools, notes and simulations are replayed from the real system, recorded on its 16 research papers. No
            model is called here and nothing you do is stored. Uploads and new questions need the full system, run locally.
          </p>
          <p className="mt-2 flex gap-3">
            <a className="underline hover:text-stone-900" href={REPO} target="_blank" rel="noreferrer">
              Source code
            </a>
            <a className="underline hover:text-stone-900" href={SHOWCASE} target="_blank" rel="noreferrer">
              Project and achievements
            </a>
          </p>
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              replayIntro();
            }}
            className="mt-2 font-medium text-stone-900 underline underline-offset-2"
          >
            Show the intro again
          </button>
        </div>
      )}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        data-tour="demo"
        className="rounded-full bg-stone-900 px-3 py-1.5 font-medium text-stone-50 shadow-md hover:bg-stone-700"
      >
        Hosted demo {open ? "×" : "ⓘ"}
      </button>
    </div>
  );
}

export function DemoSuggestions({ onPick }: { onPick: (question: string) => void }) {
  if (!DEMO) return null;
  return (
    <div className="mt-4 border-t border-stone-200 pt-4">
      <p className="text-sm font-semibold text-stone-800">Try a recorded question</p>
      <p className="mt-0.5 text-xs text-stone-500">
        This demo replays real answers. Every Studio tool works with one click, and Simulate works on the questions in its picker.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {DEMO_QUESTIONS.map((q) => (
          <button
            key={q.question}
            type="button"
            title={q.question}
            onClick={() => onPick(q.question)}
            className="rounded-full border border-stone-300 bg-stone-50 px-3 py-1 text-xs text-stone-700 hover:border-stone-500 hover:text-stone-900"
          >
            {q.label}
          </button>
        ))}
      </div>
      <button type="button" onClick={() => replayIntro()} className="mt-3 text-xs font-medium text-accent underline underline-offset-2">
        Replay the intro and tour
      </button>
    </div>
  );
}
