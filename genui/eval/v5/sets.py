"""The v5 evaluation question sets, pinned by hash (hard constraint 9: the protocol is fixed before runs; a change is a declared amendment).

    uv run python -m eval.v5.sets --status        # every set: size, approved or draft, whether its pin matches
    uv run python -m eval.v5.sets --make-r        # (re)write R.json from the library's remembered questions
    uv run python -m eval.v5.sets --pin T-gate    # record the current hash of the named sets (after the owner approves)
    uv run python -m eval.v5.sets --check         # exit 1 if any pinned set no longer matches its pin

A set file holds `approved` (false until the owner approves it) and `questions`. The pin is the SHA-256 of the file's text, so approving a set, or changing one word, changes the
hash: pin again and record the amendment in the changelog. A live run refuses a set that is unpinned, changed since its pin, or not approved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
NAMES = ("R", "T", "N", "W", "F", "T-gate")
SIZES = {"R": 10, "T": 20, "N": 10, "W": 5, "F": 10, "T-gate": 3}
LIBRARY_QUESTIONS = REPO / "data" / "library_questions.json"


def path(name: str) -> Path:
    return HERE / f"{name}.json"


def pin_path(name: str) -> Path:
    return HERE / f"{name}.sha256"


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest()


def pinned(name: str) -> bool:
    """True when the set has a pin and the file still matches it."""
    return pin_path(name).is_file() and digest(path(name)) == pin_path(name).read_text(encoding="utf-8").strip()


def load(name: str) -> dict | str:
    """The set, or the reason it may not be run: unpinned, changed since its pin, or not approved by the owner."""
    if not pin_path(name).is_file() or not pinned(name):
        return f"the set {name} does not match its pinned hash (a change is a declared amendment: approve it, then pin it with `python -m eval.v5.sets --pin {name}`)"
    data = json.loads(path(name).read_text(encoding="utf-8"))
    if not data.get("approved"):
        return f"the owner has not approved the set {name} (eval/v5/{name}.json, approved is false)"
    return data


def make_r() -> dict:
    """R: the questions the library remembers word for word. C1 must serve each in about 1 s with no model call."""
    raw = json.loads(LIBRARY_QUESTIONS.read_text(encoding="utf-8"))
    questions = []
    for lab, qs in raw.items():
        if lab.startswith("_"):
            continue
        for q in qs:
            questions.append({"id": f"r{len(questions) + 1:02d}", "question": q, "library": lab})
    return {
        "set": "R",
        "purpose": "Repeats: exact questions already in the library (data/library_questions.json). The cache must serve each in about 1 s with no model call (V5-D01). Evaluation plan section 1.",
        "status": "DRAFT written by Claude on 2026-11-17: not yet approved by the owner",
        "approved": False,
        "how_to_approve": "Set approved to true, then run: uv run python -m eval.v5.sets --pin R. The change of hash is a declared amendment (record it in the changelog).",
        "questions": questions,
    }


def status() -> list[dict]:
    rows = []
    for name in NAMES:
        p = path(name)
        if not p.is_file():
            rows.append({"set": name, "present": False})
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        rows.append(
            {
                "set": name,
                "present": True,
                "size": len(data["questions"]),
                "wanted": SIZES[name],
                "approved": bool(data.get("approved")),
                "pinned": pinned(name),
                "sha256": digest(p)[:12],
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--make-r", action="store_true")
    ap.add_argument("--pin", nargs="+", metavar="SET")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.make_r:
        path("R").write_text(json.dumps(make_r(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("wrote R.json")
    for name in args.pin or []:
        if name not in NAMES:
            print(f"unknown set {name}; the sets are {', '.join(NAMES)}")
            return 2
        pin_path(name).write_text(digest(path(name)) + "\n", encoding="utf-8")
        print(f"pinned {name}: {digest(path(name))}")
    rows = status()
    if args.status or not (args.make_r or args.pin or args.check):
        for r in rows:
            print(r if not r["present"] else f"{r['set']:7} {r['size']:>2} of {r['wanted']:<2}  {'approved' if r['approved'] else 'DRAFT   '}  {'pinned' if r['pinned'] else 'NOT pinned'}  {r['sha256']}")
    if args.check:
        bad = [r["set"] for r in rows if r["present"] and pin_path(r["set"]).is_file() and not r["pinned"]]
        if bad:
            print("sets changed since their pin:", ", ".join(bad))
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
