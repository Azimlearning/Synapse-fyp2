"use client";

// The spotlight tour of the hosted demo: the page is dimmed and one real control is lit at a time, with a speech bubble. Controls
// carry data-tour="<name>"; a stop whose control is not on this screen is left out, and the visible copy wins when a control is
// drawn twice. One box's box-shadow does the ring, the glow and the dimming, so the lit control keeps its own colours. The ring
// is the accent (not the page colour) and the dim is fixed dark, so both read in light and dark mode.

import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore, type KeyboardEvent } from "react";

export type Stop = { target: string; title: string; text: string };

export const STOPS: Stop[] = [
  { target: "views", title: "Chat", text: "Ask questions about the papers here. The answers quote their sources." },
  { target: "graph", title: "Knowledge graph", text: "The whole corpus as a graph of concepts. Open one to see its passages, cited definitions, a quiz and a review." },
  { target: "theme", title: "Light or dark", text: "Switch the colour mode at any time." },
  { target: "layout", title: "Basic or Adaptive", text: "Adaptive lets the answer arrange the workspace, adding a graph or a comparison only when the evidence supports it." },
  { target: "newchat", title: "New chat", text: "Start a fresh conversation. Past chats are kept in this browser, below this button." },
  { target: "chats", title: "Past chats", text: "Reopen, rename or delete an earlier chat." },
  { target: "sources", title: "Sample documents", text: "16 sample research papers come with the demo. In your own copy of Synapse you can delete them and upload your own." },
  { target: "ask", title: "Ask a question", text: "Ask about the papers, or pick a suggested question. Every answer quotes its sources." },
  { target: "simulate", title: "Simulate", text: "Turns the question in the box into a hands-on simulation." },
  { target: "simulations", title: "Ready-made simulations", text: "Springs, circuits, planets and ideas from the papers, ready to drag and drop." },
  { target: "studio", title: "Studio", text: "One click turns the papers into a quiz, flashcards, notes, a cheat sheet or a cited draft." },
  { target: "notes", title: "Notes", text: "Concept pages built from the papers, with their graph, a quiz and a review schedule." },
  { target: "studio-history", title: "Previous studios", text: "Every Studio output you make is kept here to reopen." },
  { target: "demo", title: "About this demo", text: "What is real here, the source code, and a way to see this intro again." },
];

type Box = { top: number; left: number; width: number; height: number };

export function findTarget(target: string): HTMLElement | null {
  for (const el of document.querySelectorAll<HTMLElement>(`[data-tour="${target}"]`)) {
    const box = el.getBoundingClientRect();
    if (box.width > 0 && box.height > 0) return el;
  }
  return null;
}

/** The target's box, re-read on resize, scroll and layout changes; the same object is returned until the numbers change. */
function useBox(target: string | null): Box | null {
  const last = useRef<Box | null>(null);
  const subscribe = useCallback((notify: () => void) => {
    window.addEventListener("resize", notify);
    window.addEventListener("scroll", notify, true);
    const observer = typeof ResizeObserver !== "undefined" ? new ResizeObserver(notify) : null;
    observer?.observe(document.body);
    return () => {
      window.removeEventListener("resize", notify);
      window.removeEventListener("scroll", notify, true);
      observer?.disconnect();
    };
  }, []);
  const read = useCallback((): Box | null => {
    const el = target ? findTarget(target) : null;
    if (!el) return (last.current = null);
    const r = el.getBoundingClientRect();
    const prev = last.current;
    if (prev && prev.top === r.top && prev.left === r.left && prev.width === r.width && prev.height === r.height) return prev;
    return (last.current = { top: r.top, left: r.left, width: r.width, height: r.height });
  }, [target]);
  return useSyncExternalStore(subscribe, read, () => null);
}

const PAD = 6;
const BUBBLE_W = 300;
const EDGE = 16;

export function Tour({ onDone }: { onDone: () => void }) {
  const stops = useMemo(() => STOPS.filter((s) => findTarget(s.target)), []);
  const [index, setIndex] = useState(0);
  const stop = stops[index] ?? null;
  const box = useBox(stop?.target ?? null);
  const next = useRef<HTMLButtonElement>(null);
  const bubble = useRef<HTMLDivElement>(null);
  const [bubbleH, setBubbleH] = useState(150);

  useEffect(() => {
    if (stops.length === 0) onDone();
  }, [stops.length, onDone]);

  useEffect(() => {
    if (!stop) return;
    findTarget(stop.target)?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
    next.current?.focus();
  }, [stop]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- the bubble's height is only known once drawn
    if (bubble.current) setBubbleH(bubble.current.offsetHeight);
  }, [index, box]);

  if (!stop || !box) return null;
  const last = index === stops.length - 1;

  // Place the bubble: right of a narrow target near the left edge, else below, else above; clamped inside the window.
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  let top: number;
  let left: number;
  let side: "right" | "below" | "above";
  if (box.left + box.width < vw * 0.3 && box.width < 320 && box.left + box.width + PAD + 14 + BUBBLE_W < vw - EDGE) {
    side = "right";
    left = box.left + box.width + PAD + 14;
    top = box.top + box.height / 2 - bubbleH / 2;
  } else if (box.top + box.height + PAD + 14 + bubbleH < vh - EDGE) {
    side = "below";
    top = box.top + box.height + PAD + 14;
    left = box.left + box.width / 2 - BUBBLE_W / 2;
  } else {
    side = "above";
    top = box.top - PAD - 14 - bubbleH;
    left = box.left + box.width / 2 - BUBBLE_W / 2;
  }
  left = Math.min(Math.max(left, EDGE), vw - EDGE - Math.min(BUBBLE_W, vw - 2 * EDGE));
  top = Math.min(Math.max(top, EDGE), vh - EDGE - bubbleH);
  const arrow =
    side === "right"
      ? { left: -6, top: Math.min(Math.max(box.top + box.height / 2 - top - 6, 12), bubbleH - 24) }
      : { top: side === "below" ? -6 : bubbleH - 6, left: Math.min(Math.max(box.left + box.width / 2 - left - 6, 16), BUBBLE_W - 28) };

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      onDone();
      return;
    }
    if (e.key !== "Tab" || !bubble.current) return;
    const items = [...bubble.current.querySelectorAll<HTMLElement>("button:not([disabled])")];
    const first = items[0];
    const end = items[items.length - 1];
    if (!first || !end) return;
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      end.focus();
    } else if (!e.shiftKey && document.activeElement === end) {
      e.preventDefault();
      first.focus();
    }
  };

  return (
    <div className="fixed inset-0 z-[60]" data-tour-overlay>
      <div
        data-spotlight
        className="pointer-events-none absolute rounded-2xl transition-all duration-200 motion-reduce:transition-none shadow-[0_0_0_3px_var(--color-accent),0_0_22px_6px_rgba(47,95,168,0.55),0_0_0_9999px_rgba(12,11,9,0.68)]"
        style={{ top: box.top - PAD, left: box.left - PAD, width: box.width + PAD * 2, height: box.height + PAD * 2 }}
      />
      <div
        ref={bubble}
        role="dialog"
        aria-modal="true"
        aria-label={`Tour of Synapse, ${stop.title}`}
        aria-describedby="tour-text"
        onKeyDown={onKeyDown}
        className="absolute rounded-2xl bg-stone-50 p-4 shadow-[0_16px_40px_rgba(0,0,0,0.28)]"
        style={{ top, left, width: Math.min(BUBBLE_W, vw - 2 * EDGE) }}
      >
        <span aria-hidden className="absolute h-3 w-3 rotate-45 bg-stone-50" style={arrow} />
        <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">
          {index + 1} of {stops.length}
        </p>
        <h2 className="mt-1 font-display text-lg font-semibold text-stone-900">{stop.title}</h2>
        <p id="tour-text" className="mt-1 text-sm leading-relaxed text-stone-600">
          {stop.text}
        </p>
        <div className="mt-3 flex items-center justify-between gap-2">
          <button type="button" onClick={onDone} className="text-sm text-stone-500 hover:text-stone-900">
            Skip tour
          </button>
          <div className="flex gap-2">
            {index > 0 && (
              <button type="button" onClick={() => setIndex(index - 1)} className="rounded-xl px-3 py-1.5 text-sm text-stone-600 hover:text-stone-900">
                Back
              </button>
            )}
            <button
              ref={next}
              type="button"
              onClick={() => (last ? onDone() : setIndex(index + 1))}
              className="rounded-xl bg-stone-900 px-4 py-1.5 text-sm font-medium text-stone-50"
            >
              {last ? "Done" : "Next"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
