// The first-run intro and tour of the hosted demo: which stage this browser is at, remembered in localStorage with an in-memory
// copy (a private window or blocked storage still never shows the slides twice in one visit). Synapse has no sign-in, so the
// "person" is the browser: one id, "visitor". Pattern from the onboarding guide (azimskill:onboarding), PaySense v2 D-53.

export type Stage = "intro" | "tour" | "done";

export const VISITOR = "visitor";
const INTRO_KEY = "synapse.intro.seen";
const TOUR_KEY = "synapse.tour.seen";

const subscribers = new Set<() => void>();
const memory = new Set<string>();
const keyFor = (base: string, id: string) => `${base}.${id}`;

function seen(base: string, id: string): boolean {
  const key = keyFor(base, id);
  if (memory.has(key)) return true;
  try {
    return window.localStorage.getItem(key) === "1";
  } catch {
    return false;
  }
}

function mark(base: string, id: string) {
  const key = keyFor(base, id);
  memory.add(key);
  try {
    window.localStorage.setItem(key, "1");
  } catch {
    // the memory mark covers this visit
  }
  subscribers.forEach((notify) => notify());
}

export function stageFor(id: string = VISITOR): Stage {
  if (!seen(INTRO_KEY, id)) return "intro";
  return seen(TOUR_KEY, id) ? "done" : "tour";
}

export const markIntroSeen = (id: string = VISITOR) => mark(INTRO_KEY, id);
export const markTourSeen = (id: string = VISITOR) => mark(TOUR_KEY, id);

/** Clear both marks so the slides show again (the "Show the intro again" control). */
export function replayIntro(id: string = VISITOR) {
  for (const base of [INTRO_KEY, TOUR_KEY]) {
    memory.delete(keyFor(base, id));
    try {
      window.localStorage.removeItem(keyFor(base, id));
    } catch {
      // nothing stored
    }
  }
  subscribers.forEach((notify) => notify());
}

export function subscribeToIntro(notify: () => void) {
  subscribers.add(notify);
  window.addEventListener("storage", notify); // another tab replaying
  return () => {
    subscribers.delete(notify);
    window.removeEventListener("storage", notify);
  };
}

/** Tests only: a reload drops the in-memory copy. */
export const forgetForTests = () => memory.clear();
