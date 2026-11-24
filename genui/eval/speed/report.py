"""The speed report (V5-0): time and cost per path, from the pipeline's trace file. Reproduces the v4 baseline in STATUS.md and is the instrument every later speed claim is
measured with (`refdocs/v5-design/docs/speed-budget.md`).

    uv run python -m eval.speed.report --traces ../Synapse-V4/data/traces.jsonl
    uv run python -m eval.speed.report --traces data/traces.jsonl --since 0

A trace line is one request: `outcome`, `records` of {layer, status, ms, detail}. The records are nested, not sequential: a layer's `ms` already includes the model call made
inside it (route 2105 holds llm:route 1785). So a request's time is the sum of its layers (every record whose name does not start with `llm:`), and its model time is the sum of
the `llm:` records. Cost is the sum of the `cost_usd` the LLM seam wrote on each `llm:` record.

This measures server time per request. The client marks (first title, first picture, usable) are a V5-4 item and are not in these files.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

PATHS = {
    "library": ("library:",),
    "compose": ("compose", "instantiate"),
    "free": ("free",),
    "text only": ("text_only",),
    "error": ("error",),
}


def load(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def layer_ms(trace: dict) -> int:
    return sum(int(r.get("ms", 0)) for r in trace.get("records", []) if not str(r.get("layer", "")).startswith("llm:"))


def model_ms(trace: dict) -> int:
    return sum(int(r.get("ms", 0)) for r in trace.get("records", []) if str(r.get("layer", "")).startswith("llm:"))


def cost_usd(trace: dict) -> float:
    return sum(float(r.get("detail", {}).get("cost_usd") or 0.0) for r in trace.get("records", []) if str(r.get("layer", "")).startswith("llm:"))


def path_of(trace: dict) -> str:
    outcome = str(trace.get("outcome", "unknown"))
    for name, prefixes in PATHS.items():
        if any(outcome == p or (p.endswith(":") and outcome.startswith(p)) for p in prefixes):
            return name
    return "other"


def percentile(values: list[float], q: float) -> float:
    """The nearest-rank percentile (q from 0 to 100), so a small sample reports a value that actually occurred."""
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q / 100 * len(ordered)) - 1)]


def summarise(rows: list[dict]) -> dict[str, dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for t in rows:
        groups[path_of(t)].append(t)
    out: dict[str, dict] = {}
    for name, ts in groups.items():
        secs = [layer_ms(t) / 1000 for t in ts]
        out[name] = {
            "n": len(ts),
            "median_s": round(statistics.median(secs), 2),
            "p90_s": round(percentile(secs, 90), 2),
            "min_s": round(min(secs), 2),
            "max_s": round(max(secs), 2),
            "model_median_s": round(statistics.median(model_ms(t) / 1000 for t in ts), 2),
            "cost_mean_usd": round(sum(cost_usd(t) for t in ts) / len(ts), 4),
            "cost_total_usd": round(sum(cost_usd(t) for t in ts), 4),
            "llm_calls_mean": round(sum(int(t.get("llm_calls", 0)) for t in ts) / len(ts), 2),
        }
    return out


def format_table(summary: dict[str, dict], total: int, source: str) -> str:
    head = f"Speed report: {total} requests from {source}\n\n"
    cols = ("path", "n", "median s", "p90 s", "min s", "max s", "model median s", "mean cost $", "total cost $", "mean LLM calls")
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for name in [n for n in ("library", "compose", "free", "text only", "error", "other") if n in summary]:
        s = summary[name]
        lines.append(
            f"| {name} | {s['n']} | {s['median_s']} | {s['p90_s']} | {s['min_s']} | {s['max_s']} | {s['model_median_s']} | {s['cost_mean_usd']} | {s['cost_total_usd']} | {s['llm_calls_mean']} |"
        )
    return head + "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", type=Path, default=Path("data/traces.jsonl"))
    ap.add_argument("--since", type=int, default=0, help="skip this many lines from the start (the file has no dates, so a window is by line)")
    ap.add_argument("--until", type=int, default=None, help="stop after this many lines from the start")
    ap.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = ap.parse_args()
    if not args.traces.is_file():
        print(f"No trace file at {args.traces}. A trace is written to DATA_DIR/traces.jsonl by every request.")
        return 2
    rows = load(args.traces)[args.since : args.until]
    if not rows:
        print("The trace file has no requests in that window.")
        return 2
    summary = summarise(rows)
    print(json.dumps(summary, indent=2) if args.json else format_table(summary, len(rows), str(args.traces)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
