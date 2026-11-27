"use client";

// The Light / Dark switch in the header (see lib/theme.ts for where the choice lives and who is told).

import { useEffect, useState } from "react";

import { readTheme, tellFrames, THEME_KEY, type UiTheme } from "@/lib/theme";

export function ThemeSwitch() {
  const [theme, setTheme] = useState<UiTheme>("light");
  // The attribute was set before paint; read it once mounted so the server render and the first client render agree.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setTheme(readTheme()), []);

  const choose = (next: UiTheme) => {
    setTheme(next);
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      /* blocked storage: the choice lasts for this visit */
    }
    tellFrames(next);
  };

  const base = "rounded-full px-3 py-1 text-xs";
  const on = `${base} bg-white font-medium text-stone-900 shadow-[0_0_0_1px_var(--color-stone-200)]`;
  const off = `${base} text-stone-600 hover:text-stone-900`;
  return (
    <div role="group" aria-label="Colour mode" data-tour="theme" className="flex gap-0.5 rounded-full border border-stone-200 bg-stone-100 p-0.5">
      <button type="button" aria-pressed={theme === "light"} onClick={() => choose("light")} className={theme === "light" ? on : off}>
        Light
      </button>
      <button type="button" aria-pressed={theme === "dark"} onClick={() => choose("dark")} className={theme === "dark" ? on : off}>
        Dark
      </button>
    </div>
  );
}
