"""Assemble a Build Script into a page (build-script.md sections 5 and 6), through the house frame in `api/pipeline/free_house.py`.

What this adds to the page, ahead of the model's own script:
- every FORMULAS line compiled to JavaScript (`formula.to_js`), recomputed whenever a control changes, and each READOUT written by Synapse from its source;
- the `host` API the model's script uses (value, on, set, found, readout, reducedMotion), and nothing else.

The model's script cannot write a readout: the validator refuses a direct write, and a readout fed from script goes through `host.readout`, the one door.

Kit parts are not mounted in this build (V5-3 brings the part host): a script that names PARTS is refused here with that reason, so nothing half-built is ever assembled.
"""

from __future__ import annotations

import json
import re

from api.buildscript import formula as fm
from api.buildscript.model import BuildScript
from api.pipeline import free_house


class AssembleError(ValueError):
    """The script cannot be assembled in this build. The message says why."""


def _js(value: object) -> str:
    # `</` is escaped so no string can close the script element, whatever a label holds.
    return json.dumps(value, ensure_ascii=True).replace("</", "<\\/")


def readout_unit(label: str) -> str:
    """The unit a readout shows after its number: the last parenthesised text of its label, or nothing."""
    m = re.search(r"\(([^()]*)\)\s*$", label.strip())
    return m.group(1).strip() if m else ""


HOST_JS = """
  var byId = Object.create(null);
  CONTROLS.forEach(function (c) { byId[c.id] = c; });
  var V = Object.create(null), prev = Object.create(null), subs = Object.create(null), fed = Object.create(null);
  var started = false;
  var reduced = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  function el(id) { return document.getElementById(id); }
  function show(r, v) {
    var o = el(r.id);
    if (o) o.textContent = (typeof v === "number" && isFinite(v)) ? v.toFixed(r.decimals) + (r.unit ? " " + r.unit : "") : "no value";
  }
  function emit(name) {
    var l = subs[name];
    if (l) for (var i = 0; i < l.length; i++) l[i](V[name]);
  }
  function recompute() {
    var names = [];
    CONTROLS.forEach(function (c) { V[c.id] = parseFloat(el(c.id).value); names.push(c.id); });
    FORMULAS.forEach(function (f) { V[f[0]] = f[1](V); names.push(f[0]); });
    READOUTS.forEach(function (r) { if (r.source !== "script") show(r, V[r.source]); });
    names.forEach(function (n) { if (!started || V[n] !== prev[n]) emit(n); prev[n] = V[n]; });
  }
  CONTROLS.forEach(function (c) { el(c.id).addEventListener("input", recompute); });
  return {
    value: function (name) { return V[name]; },
    on: function (name, fn) {
      (subs[name] = subs[name] || []).push(fn);
      if (started) fn(V[name]);
    },
    set: function (id, value) {
      var c = byId[id];
      if (!c || typeof value !== "number" || !isFinite(value)) return;
      var v = c.min + Math.round((value - c.min) / c.step) * c.step;
      v = Number(Math.min(c.max, Math.max(c.min, v)).toFixed(10));
      var e = el(id);
      e.value = String(v);
      e.dispatchEvent(new Event("input", { bubbles: true }));
    },
    found: function (text) { var f = el("found"); if (f) f.textContent = String(text); },
    readout: function (id, value) {
      fed[id] = value;
      READOUTS.forEach(function (r) { if (r.id === id && r.source === "script") show(r, value); });
    },
    reducedMotion: reduced,
    start: function () { started = true; recompute(); READOUTS.forEach(function (r) { if (r.source === "script" && fed[r.id] !== undefined) show(r, fed[r.id]); }); }
  };
"""


def prelude(bs: BuildScript) -> str:
    """The JavaScript that defines `host`, ahead of the model's script."""
    controls = [{"id": c.id, "min": c.min, "max": c.max, "step": c.step} for c in bs.controls]
    readouts = [{"id": r.id, "source": r.source, "decimals": r.decimals, "unit": readout_unit(r.label)} for r in bs.readouts]
    formulas = ",\n    ".join(f"[{_js(f.name)}, function (V) {{ return {fm.to_js(fm.parse(f.expr))}; }}]" for f in bs.formulas)
    return (
        "var host = (function () {\n"
        f"  {fm.JS_HELPERS}\n"
        f"  var CONTROLS = {_js(controls)};\n"
        f"  var READOUTS = {_js(readouts)};\n"
        f"  var FORMULAS = [\n    {formulas}\n  ];\n"
        f"{HOST_JS}"
        "})();"
    )


def assemble(bs: BuildScript) -> str:
    """The whole page. Raises AssembleError for a script this build cannot assemble."""
    if bs.parts:
        raise AssembleError("Kit parts are not mounted in this build (they arrive with V5-3): write the Environment without @@PARTS, or list none")
    if not bs.drawing or not bs.controls or not bs.readouts:
        raise AssembleError("a Build Script needs a drawing, at least one control and at least one readout to be assembled")
    lab = free_house.Lab(
        title=bs.title[:60],
        kicker=bs.kicker[:60] or "Virtual Environment",
        try_this=bs.try_this,
        idea=bs.idea[:3],
        predict=bs.predict,
        steps=bs.steps[:6],
        hints=bs.hints[:4],
        explain=bs.explain[:4],
        drawing=bs.drawing,
        style=bs.style,
        controls=bs.controls,
        readouts=[free_house.Readout(r.id, r.label) for r in bs.readouts],
        script=f"{prelude(bs)}\n{bs.script}\nhost.start();",
    )
    return free_house.assemble(lab)


def reference_values(bs: BuildScript, controls: dict[str, float]) -> dict[str, float]:
    """The Python reference for every formula at the given control values: what the page must show. Raises FormulaError where a value has no value."""
    env = {c.id: float(controls[c.id]) for c in bs.controls}
    for f in bs.formulas:
        env[f.name] = fm.evaluate(fm.parse(f.expr), env)
    return env
