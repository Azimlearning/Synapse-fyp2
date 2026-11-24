"""The V5-2 live gate (V5-D17: evaluation is live, never on fakes). Not part of the test suite: it makes real model calls.

    uv run python -m eval.buildscript.gate --one     # the first question only: is the harness alive?
    uv run python -m eval.buildscript.gate           # all three questions

What it refuses to do, on purpose:
- run on a question set that is not pinned by hash, or that the owner has not approved (hard constraint 9: the set is fixed before the run);
- spend. It forces ALLOW_PAID_FALLBACK off, so only free models can answer; a request the free chain cannot serve fails and is reported, never sent to a paid key.

It reads the settings (and so the key) inside this process and never prints a key. Pages and the summary are written to eval/v5/results/<time>/ so the owner can judge the
pages blind, next to v4's Free pages for the same questions.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from api import kitmanifest
from api.buildscript.gate import build_all, check_all, format_report, summarise
from api.core.settings import Settings
from api.kit import latest_version
from api.llm.factory import build_ledger, build_llm_service
from eval.v5 import sets

REPO = Path(__file__).resolve().parents[2]
SET = sets.path("T-gate")
PIN = sets.pin_path("T-gate")
RESULTS = REPO / "eval" / "v5" / "results"


digest = sets.digest


def load_set() -> dict | str:
    """The question set, or the reason it may not be run."""
    if not PIN.is_file() or digest(SET) != PIN.read_text(encoding="utf-8").strip():
        return "the question set does not match its pinned hash (a change is a declared amendment: approve it, then run `python -m eval.v5.sets --pin T-gate`)"
    data = json.loads(SET.read_text(encoding="utf-8"))
    if not data.get("approved"):
        return "the owner has not approved the question set (eval/v5/T-gate.json, approved is false)"
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--one", action="store_true", help="run only the first question")
    args = ap.parse_args()
    data = load_set()
    if isinstance(data, str):
        print("Not run:", data)
        return 2
    if not (REPO / ".env").exists():
        print("No .env in the repository folder (refdocs/guides/env_setup.md).")
        return 2
    settings = Settings(_env_file=REPO / ".env", synapse_llm_mode="live", allow_paid_fallback=False)  # type: ignore[call-arg]
    missing = settings.missing_for_mode()
    if missing:
        print("Not ready:", "; ".join(f"{name}: {why}" for name, why in missing))
        return 2
    service = build_llm_service(settings, build_ledger(settings))
    kit_dist = REPO / "packages" / "kit" / "dist"
    manifest = kitmanifest.load(kit_dist, latest_version(kit_dist))
    questions = data["questions"][:1] if args.one else data["questions"]
    print(f"{len(questions)} question(s); provider: {service._providers[0].name}; paid fallback built: {len(service._providers) > 1}")  # noqa: SLF001
    items = asyncio.run(build_all(service, questions, manifest))
    check_all(items, kit_dist=kit_dist)
    summary = summarise(items)
    out = RESULTS / time.strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    for item in items:
        if item.built and item.built.html:
            (out / f"{item.id}.html").write_text(item.built.html, encoding="utf-8")
        if item.built and item.built.raw_script:
            (out / f"{item.id}.buildscript.txt").write_text(item.built.raw_script, encoding="utf-8")
    print(format_report(summary))
    print(f"\nwritten to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
