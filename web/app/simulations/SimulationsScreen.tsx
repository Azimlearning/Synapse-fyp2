"use client";

// The Simulations view: the generative UI side of Synapse. Ask a science question and get an interactive simulation that was
// run and checked in a real browser before it is shown, with its source and trust label. It is served by the Synapse
// simulation engine (genui/: its own API, verifier and sandbox host; `NEXT_PUBLIC_SIMULATIONS_URL`, default
// http://localhost:3001) and shown here inside the Synapse shell. That app is a different origin, so it can never read this
// page, and each simulation inside it runs in its own sandboxed iframe. It opens in this page's colour mode and is told when
// the header's switch changes it.

import { useEffect, useState } from "react";

import { AppNav } from "@/components/shell/AppNav";
import { readTheme, SIMULATIONS_URL, type UiTheme } from "@/lib/theme";

export function SimulationsScreen() {
  const [key, setKey] = useState(0);
  // The frame's first theme comes from the page, which is only known in the browser: the frame is drawn once that is read.
  const [startTheme, setStartTheme] = useState<UiTheme | null>(null);
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setStartTheme(readTheme()), []);

  return (
    <div className="flex h-screen flex-col bg-stone-50 text-stone-900">
      <header className="flex items-center justify-between gap-4 border-b border-stone-200 bg-stone-50 px-6 py-3">
        <AppNav current="simulations" />
        <div className="flex items-center gap-3">
          <span className="hidden font-serif text-sm italic text-stone-500 xl:inline">generative UI, verified in a real browser</span>
          <button
            type="button"
            onClick={() => {
              setStartTheme(readTheme());
              setKey((k) => k + 1);
            }}
            className="rounded-full border border-stone-300 bg-white px-3 py-1 text-xs text-stone-600 hover:text-stone-900"
          >
            New session
          </button>
        </div>
      </header>
      {startTheme && (
        <iframe
          key={key}
          data-simulations
          title="Synapse simulations"
          src={`${SIMULATIONS_URL}/?embed=1&theme=${startTheme}`}
          className="min-h-0 w-full flex-1 border-0 bg-stone-50"
          allow="clipboard-write; fullscreen"
        />
      )}
    </div>
  );
}
