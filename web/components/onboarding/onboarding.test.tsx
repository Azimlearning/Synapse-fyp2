import { readFileSync } from "node:fs";
import { join } from "node:path";

import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { forgetForTests, markIntroSeen, markTourSeen, replayIntro, stageFor } from "@/lib/introTour";

import { Intro, SLIDES } from "./Intro";
import { OnboardingGate } from "./OnboardingGate";
import { STOPS, Tour } from "./Tour";

beforeEach(() => forgetForTests());

describe("introTour store", () => {
  it("moves from intro to tour to done, and replay starts over", () => {
    expect(stageFor()).toBe("intro");
    markIntroSeen();
    expect(stageFor()).toBe("tour");
    markTourSeen();
    expect(stageFor()).toBe("done");
    replayIntro();
    expect(stageFor()).toBe("intro");
  });

  it("is kept per id and survives a reload through localStorage", () => {
    markIntroSeen("a");
    markTourSeen("a");
    forgetForTests();
    expect(stageFor("a")).toBe("done");
    expect(stageFor("b")).toBe("intro");
  });

  it("falls back to memory when storage throws", () => {
    const spy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    markIntroSeen();
    expect(stageFor()).toBe("tour");
    spy.mockRestore();
  });
});

describe("Intro", () => {
  it("opens as a dialog on slide 1 with focus inside, and Next and Back move one slide", () => {
    render(<Intro onTour={() => {}} onSkip={() => {}} />);
    const dialog = screen.getByRole("dialog", { name: "Welcome to Synapse" });
    expect(dialog).toHaveFocus();
    expect(screen.getByText(SLIDES[0]!.title)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByText(SLIDES[1]!.title)).toBeInTheDocument();
    expect(document.querySelector("[data-intro-card]")).toHaveClass("ob-in-next");
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByText(SLIDES[0]!.title)).toBeInTheDocument();
    expect(document.querySelector("[data-intro-card]")).toHaveClass("ob-in-back");
  });

  it("offers the tour or a way out on the last slide", () => {
    const onTour = vi.fn();
    render(<Intro onTour={onTour} onSkip={() => {}} />);
    for (let i = 1; i < SLIDES.length; i++) fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("button", { name: "Skip the tour" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Take a quick tour" }));
    expect(onTour).toHaveBeenCalledOnce();
  });

  it("skips on Escape", () => {
    const onSkip = vi.fn();
    render(<Intro onTour={() => {}} onSkip={onSkip} />);
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(onSkip).toHaveBeenCalledOnce();
  });

  it("says plainly that this is a recorded demo", () => {
    expect(SLIDES[2]!.text).toMatch(/recorded from the real system/);
  });
});

describe("motion CSS", () => {
  it("has the keyframes and a reduced-motion block that also clears delays and loops", () => {
    const css = readFileSync(join(process.cwd(), "app", "globals.css"), "utf-8");
    expect(css).toMatch(/@keyframes intro-draw/);
    expect(css).toMatch(/@keyframes ob-in-next/);
    expect(css).toMatch(/prefers-reduced-motion: reduce[\s\S]*animation-delay: 0s !important[\s\S]*animation-iteration-count: 1 !important/);
  });
});

describe("Tour", () => {
  const boxes = new Map<string, DOMRect>();
  let rectSpy: ReturnType<typeof vi.spyOn>;
  beforeEach(() => {
    rectSpy = vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
      return boxes.get(this.dataset.tour ?? "") ?? new DOMRect(0, 0, 0, 0);
    });
  });
  afterEach(() => {
    rectSpy.mockRestore();
    boxes.clear();
  });

  function page(targets: string[]) {
    for (const t of targets) boxes.set(t, new DOMRect(100, 100, 120, 40));
    return (
      <div>
        {STOPS.map((s) => (
          <button key={s.target} data-tour={s.target}>
            {s.target}
          </button>
        ))}
      </div>
    );
  }

  it("leaves out a stop whose control is not on screen, and walks Next, Back and Done", () => {
    const onDone = vi.fn();
    render(page(["ask", "studio"]));
    render(<Tour onDone={onDone} />);
    expect(screen.getByText("1 of 2")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ask a question" })).toBeInTheDocument();
    expect(document.querySelector("[data-spotlight]")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByRole("heading", { name: "Studio" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByRole("heading", { name: "Ask a question" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    fireEvent.click(screen.getByRole("button", { name: "Done" }));
    expect(onDone).toHaveBeenCalledOnce();
  });

  it("ends at once when no control is on screen, and on Escape", () => {
    const none = vi.fn();
    render(<Tour onDone={none} />);
    expect(none).toHaveBeenCalled();
    const esc = vi.fn();
    render(page(["ask"]));
    render(<Tour onDone={esc} />);
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(esc).toHaveBeenCalledOnce();
  });

  it("rings the spotlight in the accent, not the page colour, so it shows in dark mode", () => {
    render(page(["ask"]));
    render(<Tour onDone={() => {}} />);
    const cls = document.querySelector("[data-spotlight]")!.className;
    expect(cls).toContain("var(--color-accent)");
    expect(cls).not.toContain("stone-50");
  });
});

describe("OnboardingGate", () => {
  it("shows nothing outside the demo", () => {
    render(<OnboardingGate enabled={false}>page</OnboardingGate>);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("makes the page inert while the intro shows, and lets it go when skipped", () => {
    render(
      <OnboardingGate enabled>
        <p>page</p>
      </OnboardingGate>,
    );
    expect(screen.getByText("page").parentElement).toHaveAttribute("inert");
    act(() => {
      fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByText("page").parentElement).not.toHaveAttribute("inert");
    expect(stageFor()).toBe("done");
  });

  it("comes back after a replay", () => {
    markIntroSeen();
    markTourSeen();
    render(<OnboardingGate enabled>page</OnboardingGate>);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    act(() => replayIntro());
    expect(screen.getByRole("dialog", { name: "Welcome to Synapse" })).toBeInTheDocument();
  });
});
