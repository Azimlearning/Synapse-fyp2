"use client";

// The first-run flow of the hosted demo (NEXT_PUBLIC_DEMO=1 only): the welcome slides, then the spotlight tour, once per browser,
// replayable from the Hosted demo badge. Mounted once in the root layout around the page. Nothing is drawn before hydration (the
// server snapshot is "done"), and while either shows the page behind is inert, so nothing there can take focus.

import { useEffect, useRef, useSyncExternalStore, type ReactNode } from "react";

import { DEMO } from "@/components/shell/DemoNotice";
import { markIntroSeen, markTourSeen, stageFor, subscribeToIntro } from "@/lib/introTour";

import { Intro } from "./Intro";
import { Tour } from "./Tour";

export function OnboardingGate({ children, enabled = DEMO }: { children?: ReactNode; enabled?: boolean }) {
  const stage = useSyncExternalStore(
    subscribeToIntro,
    () => (enabled ? stageFor() : "done"),
    () => "done" as const,
  );
  const active = stage !== "done";
  const wasActive = useRef(active);

  useEffect(() => {
    // Give focus back to the page when the flow ends: the question box where there is one.
    if (wasActive.current && !active) document.querySelector<HTMLElement>('[data-tour="ask"] input')?.focus();
    wasActive.current = active;
  }, [active]);

  return (
    <>
      {children !== undefined && <div inert={active}>{children}</div>}
      {stage === "intro" && (
        <Intro
          onTour={() => markIntroSeen()}
          onSkip={() => {
            markIntroSeen();
            markTourSeen();
          }}
        />
      )}
      {stage === "tour" && <Tour onDone={() => markTourSeen()} />}
    </>
  );
}
