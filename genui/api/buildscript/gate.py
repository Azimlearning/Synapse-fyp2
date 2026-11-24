"""The V5-2 prototype gate (evaluation-plan.md section 3): run 3 twist questions through the Blueprint and the Build Script, check each page in a real browser, and
judge the four go criteria.

Two steps, kept apart because the browser checks use Playwright's synchronous API, which cannot run inside an asyncio loop:

    results = asyncio.run(build_all(service, questions, manifest))   # the model calls
    check_all(results, kit_dist=...)                                  # the real-browser checks
    summary = summarise(results)

The criteria, as the plan states them:

1. median tokens out of the writer is 2,500 or fewer (thinking included, as the provider reports it);
2. median writer time is 20 seconds or less. Set for a paid standard-tier model: on free models a miss is reported as such and is NOT by itself a no-go (ASSUMED A-V5-2-1);
3. at least 2 of 3 scripts validate and pass the existing Free checks on the first or second attempt;
4. the owner judges the 3 Environments at least as good as v4's Free ones. A person's call: this module only records it as pending.

The model-judged scores are never a criterion (hard constraint 9). The Blueprint's expected behaviours, run in the browser, are reported next to the criteria as the
strongest evidence the pages do what their plans said.
"""

from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path

from api.blueprint.behaviour import compile_behaviours
from api.buildscript.sweep import sweep_page
from api.buildscript.writer import Built, Service, build
from api.kit import latest_version
from api.kitmanifest import Manifest
from api.pipeline.grounding import UNCHECKED_CITATION
from api.verify.mint import VerificationFailed, verify_environment

MAX_MEDIAN_WRITER_TOKENS = 2500
MAX_MEDIAN_WRITER_SECONDS = 20.0
MIN_PASSING = 2


@dataclass
class Item:
    id: str
    question: str
    built: Built | None = None
    verified: bool = False
    verify_reason: str = ""
    behaviours: list[dict] = field(default_factory=list)

    @property
    def writer_tokens(self) -> int:
        return sum(c.tokens_out for c in self.built.calls_for("build_script")) if self.built else 0

    @property
    def writer_seconds(self) -> float:
        return sum(c.seconds for c in self.built.calls_for("build_script")) if self.built else 0.0

    @property
    def passed(self) -> bool:
        """Validated and assembled on the first or second attempt (the writer allows two) and survived the real browser's Free checks."""
        return bool(self.built and self.built.ok and self.verified)


async def build_all(service: Service, questions: list[dict], manifest: Manifest, stored_ids: frozenset[str] = frozenset()) -> list[Item]:
    items = []
    for q in questions:
        item = Item(q["id"], q["question"])
        item.built = await build(service, q["question"], manifest, stored_ids)
        items.append(item)
    return items


def check_all(items: list[Item], *, kit_dist: Path, public_origin: str = "http://localhost:3000") -> None:
    """The real-browser checks for every item whose script assembled: the verifier every Free page faces, then the Blueprint's behaviours."""
    for item in items:
        b = item.built
        if b is None or not b.ok or b.html is None or b.script is None or b.blueprint is None:
            continue
        try:
            verify_environment(
                slug=f"v5_2_gate_{item.id}",
                title=b.script.title,
                raw_html=b.html,
                lane="free",
                label="model-checked",
                kit_version=latest_version(kit_dist),
                citations=[UNCHECKED_CITATION],
                plan_summary="A Build Script written for the V5-2 gate.",
                public_origin=public_origin,
                kit_dist=kit_dist,
                interaction_seconds=1.0,
                plan_models=None,
            )
            item.verified = True
        except VerificationFailed as exc:
            item.verify_reason = f"{exc}"
        results = sweep_page(b.html, b.script, compile_behaviours(b.blueprint))
        item.behaviours = [{"text": s.text, "ok": v.ok, "reason": v.reason} for s, v in results]


def summarise(items: list[Item]) -> dict:
    tokens = [i.writer_tokens for i in items if i.built and i.built.calls_for("build_script")]
    seconds = [i.writer_seconds for i in items if i.built and i.built.calls_for("build_script")]
    med_tokens = statistics.median(tokens) if tokens else None
    med_seconds = statistics.median(seconds) if seconds else None
    passing = sum(1 for i in items if i.passed)
    c1 = med_tokens is not None and med_tokens <= MAX_MEDIAN_WRITER_TOKENS
    c2 = med_seconds is not None and med_seconds <= MAX_MEDIAN_WRITER_SECONDS
    c3 = passing >= MIN_PASSING
    hard_ok = c1 and c3
    return {
        "criteria": {
            "median_writer_tokens_out": {"value": med_tokens, "limit": MAX_MEDIAN_WRITER_TOKENS, "met": c1},
            "median_writer_seconds": {"value": None if med_seconds is None else round(med_seconds, 1), "limit": MAX_MEDIAN_WRITER_SECONDS, "met": c2,
                                      "note": "set for a paid standard-tier model; on free models a miss is not by itself a no-go (A-V5-2-1)"},
            "scripts_passing": {"value": passing, "limit": MIN_PASSING, "of": len(items), "met": c3},
            "owner_judgement": {"value": "pending", "met": None},
        },
        "automatic_verdict": "GO pending the owner's blind judgement" if hard_ok else "NO-GO",
        "time_criterion_missed_only": hard_ok and not c2,
        "cost_usd": round(sum(i.built.cost_usd for i in items if i.built), 6),
        "items": [
            {
                "id": i.id,
                "question": i.question,
                "ok": i.built.ok if i.built else False,
                "verified": i.verified,
                "verify_reason": i.verify_reason,
                "reason": i.built.reason if i.built else "",
                "writer_tokens_out": i.writer_tokens,
                "writer_seconds": round(i.writer_seconds, 1),
                "calls": [asdict(c) for c in i.built.calls] if i.built else [],
                "behaviours": i.behaviours,
            }
            for i in items
        ],
    }


def format_report(summary: dict) -> str:
    lines = ["V5-2 prototype gate", ""]
    for i in summary["items"]:
        state = "PASSED" if i["ok"] and i["verified"] else "FAILED"
        models = ", ".join(sorted({c["model"] for c in i["calls"] if c["model"]})) or "none"
        lines.append(f"{i['id']}  {state}  writer {i['writer_tokens_out']} tokens, {i['writer_seconds']} s; models: {models}")
        lines.append(f"    {i['question']}")
        for why in (i["reason"], i["verify_reason"]):
            if why:
                lines.append(f"    why: {why[:240]}")
        for b in i["behaviours"]:
            lines.append(f"    behaviour {'ok  ' if b['ok'] else 'FAIL'} {b['text']}" + ("" if b["ok"] else f" ({b['reason'][:120]})"))
    lines.append("")
    for name, c in summary["criteria"].items():
        met = {True: "met", False: "NOT met", None: "pending"}[c["met"]]
        lines.append(f"{name}: {c['value']} (limit {c.get('limit', '-')}) {met}" + (f"   [{c['note']}]" if c.get("note") else ""))
    lines.append("")
    lines.append(f"verdict: {summary['automatic_verdict']}" + ("  (only the time criterion was missed, on free models)" if summary["time_criterion_missed_only"] else ""))
    lines.append(f"spent: ${summary['cost_usd']:.4f}")
    return "\n".join(lines)
