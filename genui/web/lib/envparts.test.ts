import { describe, expect, it } from "vitest";

import { EMBED_BENCH_ONLY_STYLE, envParts } from "./envparts";

const HTML = `<html><head><title>x</title></head><body><script>
  var env = Synapse.environment({ title: "Hooke's law: how does a spring stretch?", note: "Within the elastic limit, extension = load / k.", kicker: "Interactive physics lab", tryThis: "Investigate the extension." });
  Synapse.stepper(env, {"steps": ["Hang 2 N, then press Record.", "Hang 4 N."]});
  Synapse.predictCard(env, {"prompt": "What if you double the load?", "choices": ["Less", "Double", "Same"], "reveal": "It doubles."});
  Synapse.conceptCheck(env, {"question": "Load doubled: extension?", "options": ["Halves", "Doubles", "Same"], "correct": 1, "explanation": "Proportional."});
  Synapse.hintLadder(env, { hints: ["Look at the graph.", "Compare two loads."] });
  Synapse.text(env, "Move the slider.");
  Synapse.experiment(env, {"aim": "Find k", "hypothesis": "h", "independent": "Load", "dependent": "Extension", "controlled": ["Same spring"], "apparatus": ["Spring"]});
  Synapse.bridge.ready();
</script></body></html>`;

describe("envParts", () => {
  it("reads the heading, steps, hints, texts, experiment and questions from the Kit calls as text", () => {
    const p = envParts(HTML);
    expect(p.title).toBe("Hooke's law: how does a spring stretch?");
    expect(p.kicker).toBe("Interactive physics lab");
    expect(p.tryThis).toBe("Investigate the extension.");
    expect(p.keyIdea).toBe("Within the elastic limit, extension = load / k.");
    expect(p.steps).toEqual(["Hang 2 N, then press Record.", "Hang 4 N."]);
    expect(p.hints).toEqual(["Look at the graph.", "Compare two loads."]);
    expect(p.texts).toEqual(["Move the slider."]);
    expect(p.predicts).toEqual([{ prompt: "What if you double the load?", choices: ["Less", "Double", "Same"], reveal: "It doubles." }]);
    expect(p.checks).toEqual([{ question: "Load doubled: extension?", options: ["Halves", "Doubles", "Same"], correct: 1, explanation: "Proportional." }]);
    expect(p.experiment?.aim).toBe("Find k");
  });

  it("leaves out what does not parse and never throws", () => {
    const p = envParts(`<script>Synapse.environment({ title: "T" ); Synapse.conceptCheck(env, {"question": "Q", "options": ["a"], "correct": 5});</script>`);
    expect(p.checks).toEqual([]);
    expect(p.steps).toEqual([]);
  });

  it("reads the words of a Free-lane page from its house frame, as text", () => {
    const html =
      '<html><body><main class="lab"><header><p class="kicker">Virtual lab</p><h1>Pendulum</h1><p class="try"><strong>Try this:</strong> Drag the knob.</p></header>' +
      '<div class="top"><section class="card idea"><h2>Key idea</h2><p>Longer swings slower.</p></section>' +
      '<section class="card predict"><h2>Predict first</h2><p>4 times longer?</p><ul><li>2x</li><li>4x</li></ul><details><summary>Check</summary><p>2x.</p></details></section></div>' +
      '<section class="card steps"><h2>Steps</h2><ol><li>Drag to 0.25 m.</li><li>Drag to 1 m.</li></ol></section>' +
      '<section class="card hints"><h2>Need a hint?</h2><details><summary>Hint 1</summary><p>Watch T.</p></details></section></main>' +
      "<script>window.bad = 1</script></body></html>";
    const p = envParts(html);
    expect(p.title).toBe("Pendulum");
    expect(p.tryThis).toBe("Drag the knob.");
    expect(p.keyIdea).toBe("Longer swings slower.");
    expect(p.steps).toEqual(["Drag to 0.25 m.", "Drag to 1 m."]);
    expect(p.hints).toEqual(["Watch T."]);
    expect(p.predicts).toEqual([{ prompt: "4 times longer?", choices: ["2x", "4x"], reveal: "2x." }]);
    expect((window as unknown as { bad?: number }).bad).toBeUndefined();
  });
});

describe("EMBED_BENCH_ONLY_STYLE", () => {
  // The Kit's self-audit closes an Environment whose added stylesheet matches these (packages/kit/src/audit.ts). `align-content:` and
  // `justify-content:` match the first one, which closed every Kit Environment once (2026-11-24).
  const STYLE_FORBIDDEN = /@font-face|@import|url\s*\(|image-set\s*\(|\bcontent\s*:/i;
  const MARKER_FORBIDDEN = /@counter-style\b|\bcounter-(?:reset|set|increment)\b|\bcounters?\s*\(|::?marker\b|\blist-style(?:-type)?\s*:[^;}]*["']|\bdisplay\s*:\s*(?:list-item|inline list-item|block list-item)/i;
  it("passes the Kit's stylesheet audit", () => {
    expect(STYLE_FORBIDDEN.test(EMBED_BENCH_ONLY_STYLE)).toBe(false);
    expect(MARKER_FORBIDDEN.test(EMBED_BENCH_ONLY_STYLE)).toBe(false);
  });
});
