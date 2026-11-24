// The colour mode. Light is the default (a system dark preference is not followed: the app is presented light). The choice lives on
// <html data-theme>, set before first paint by THEME_SCRIPT in the root layout, and is remembered in this browser. The embedded
// simulations are a different origin, so they are told by message (`synapse_host_theme`).

export type UiTheme = "light" | "dark";
export const THEME_KEY = "synapse-ui-theme";
export const SIMULATIONS_URL = (process.env.NEXT_PUBLIC_SIMULATIONS_URL ?? "http://localhost:3001").replace(/\/$/, "");
export const SIMULATIONS_ORIGIN = new URL(SIMULATIONS_URL).origin;

/** Runs before first paint (root layout): the remembered choice, else light. */
export const THEME_SCRIPT = `try{var t=localStorage.getItem('${THEME_KEY}');document.documentElement.dataset.theme=(t==='dark'?'dark':'light');}catch(e){document.documentElement.dataset.theme='light';}`;

export function readTheme(): UiTheme {
  if (typeof document === "undefined") return "light";
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

/** Tell every embedded simulations frame the theme. */
export function tellFrames(theme: UiTheme): void {
  document.querySelectorAll<HTMLIFrameElement>("iframe[data-simulations]").forEach((f) => {
    f.contentWindow?.postMessage({ type: "synapse_host_theme", theme }, SIMULATIONS_ORIGIN);
  });
}
