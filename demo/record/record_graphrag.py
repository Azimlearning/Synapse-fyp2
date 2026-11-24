"""Record the GraphRAG API's real responses for the hosted demo (web/demo-data/graphrag/).

The hosted demo has no Python backend: its route handler (web/app/demo-api/[...path]/route.ts) replays what this script saved.
Run it against a local API started on a COPY of the corpus (the quiz answers record learner events):

    ARCANA_DATA_DIR=data/demo-record uv run uvicorn api.main:app --port 8000
    uv run python demo/record/record_graphrag.py [--skip-chat] [--only-chat]

GET views (workspace, notes, quiz, lint, labs, patterns) cost nothing. Chat turns run the live model when the API is in live
mode, so every question in CHAT is paid once; a question already saved is not asked again unless --rechat is given.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://localhost:8000"
OUT = Path(__file__).resolve().parents[2] / "web" / "demo-data" / "graphrag"

# The questions a visitor can replay. Studio starters are recorded on the topics the corpus covers best.
# One click on a Studio tool with an empty question box asks "<tool request><best connected concept>", which is "retrieval" on
# this corpus (Workspace.tsx defaultTopic), so those exact requests are recorded first.
STUDIO_TOPIC = "retrieval"
STUDIO = [
    "Quiz me on ", "Make flashcards for ", "Make a blurting exercise for ", "Give me cornell notes on ",
    "Guide me with socratic questions about ", "Brief me on ", "Make a cheat sheet for ", "Write an outline on ",
    "Write a literature review of ", "Write an abstract on ", "Make an audio overview of ",
]
CHAT = [s + STUDIO_TOPIC for s in STUDIO] + [
    "Show my learning insights",
    "What should I review today?",
    "How do GraphRAG, LightRAG and HippoRAG compare in how they use a knowledge graph for retrieval?",
    "What is reciprocal rank fusion and how does HybridRAG combine graph and vector retrieval?",
    "What failure modes of vector-only retrieval are identified across the papers?",
    "What is multi-hop question answering, and why is it hard for vector-only retrieval?",
    "How does chunk size affect retrieval quality?",
    "What is open information extraction and how is it used to build a knowledge graph?",
    "How is retrieval-augmented generation evaluated, and what does RAGAS measure?",
    "Why does a spring stretch when I hang a weight on it?",
    "Who won the 2022 FIFA World Cup?",
    "Quiz me on GraphRAG",
    "Make flashcards for GraphRAG",
    "Make a cheat sheet for GraphRAG",
]

NOTE_QUERIES = ["knowledge graphs", "GraphRAG", "retrieval", "vector", "LightRAG", "HippoRAG", "RAGAS", "chunk", "entity", "multi-hop"]
MAX_PAGES = 120


def key_of(method: str, path: str, query: dict[str, str] | None = None) -> str:
    q = urllib.parse.urlencode(sorted((query or {}).items()))
    return f"{method} {path}" + (f"?{q}" if q else "")


def file_of(key: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")[:60]
    return f"{slug}-{hashlib.sha1(key.encode()).hexdigest()[:10]}.json"


class Recorder:
    def __init__(self) -> None:
        (OUT / "get").mkdir(parents=True, exist_ok=True)
        (OUT / "chat").mkdir(parents=True, exist_ok=True)
        self.index_path = OUT / "routes.json"
        self.routes: dict[str, dict] = json.loads(self.index_path.read_text("utf-8")) if self.index_path.exists() else {}

    def save(self, key: str, status: int, body: bytes) -> None:
        name = file_of(key)
        (OUT / "get" / name).write_bytes(body)
        self.routes[key] = {"status": status, "file": f"get/{name}"}

    def get(self, path: str, query: dict[str, str] | None = None) -> object | None:
        key = key_of("GET", path, query)
        url = BASE + path + (("?" + urllib.parse.urlencode(query)) if query else "")
        try:
            with urllib.request.urlopen(url, timeout=300) as r:
                body, status = r.read(), r.status
        except urllib.error.HTTPError as e:
            body, status = e.read(), e.code
        self.save(key, status, body)
        try:
            return json.loads(body) if status == 200 else None
        except ValueError:
            return None

    def post_json(self, path: str, payload: dict) -> tuple[int, object]:
        req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(), headers={"content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"null")

    def write_index(self) -> None:
        self.index_path.write_text(json.dumps(self.routes, indent=1, sort_keys=True), "utf-8")


def walk(value: object, found: set[str], pattern: re.Pattern[str]) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, str) and pattern.fullmatch(v):
                found.add(v)
            walk(v, found, pattern)
    elif isinstance(value, list):
        for v in value:
            walk(v, found, pattern)
    elif isinstance(value, str) and pattern.fullmatch(value):
        found.add(value)


def page_ids(view: object) -> list[str]:
    """Concept page ids in a notes view, most connected first (the graph's nodes carry the id and a weight when present)."""
    ids: list[tuple[float, str]] = []

    def visit(v: object) -> None:
        if isinstance(v, dict):
            # A NotesGraph node: {id, label, kind, passages, documents, degree, mastery}; its id is the concept page's id.
            pid = v.get("id") if {"label", "kind", "passages"} <= v.keys() else None
            if isinstance(pid, str):
                w = v.get("passages") or 0
                ids.append((float(w) if isinstance(w, (int, float)) else 0.0, pid))
            for x in v.values():
                visit(x)
        elif isinstance(v, list):
            for x in v:
                visit(x)

    visit(view)
    seen: dict[str, float] = {}
    for w, pid in ids:
        seen[pid] = max(w, seen.get(pid, 0.0))
    return [pid for pid, _ in sorted(seen.items(), key=lambda kv: -kv[1])]


def record_views(rec: Recorder) -> None:
    for path in ("/health", "/workspace", "/vault/lint", "/labs", "/patterns"):
        rec.get(path)
        print("saved", path, flush=True)
    index = rec.get("/vault/notes")
    rec.get("/vault/quiz")
    pages = page_ids(index)
    for q in NOTE_QUERIES:
        pages += page_ids(rec.get("/vault/notes", {"query": q}))
    order = list(dict.fromkeys(pages))[:MAX_PAGES]
    print(len(order), "concept pages", flush=True)
    quizzes = []
    for i, pid in enumerate(order):
        rec.get("/vault/notes", {"page": pid})
        quizzes.append(rec.get("/vault/quiz", {"page": pid}))
        if i % 20 == 0:
            print(" page", i, pid, flush=True)
            rec.write_index()
    rec.write_index()
    record_quiz_answers(rec, [rec_quiz for rec_quiz in quizzes if rec_quiz] + [json.loads((OUT / rec.routes[key_of("GET", "/vault/quiz")]["file"]).read_text("utf-8"))])


def quiz_items(value: object) -> list[dict]:
    items: list[dict] = []

    def visit(v: object) -> None:
        if isinstance(v, dict):
            if isinstance(v.get("itemId"), str) and isinstance(v.get("options"), list):
                items.append(v)
            elif isinstance(v.get("id"), str) and isinstance(v.get("options"), list) and v.get("options"):
                items.append({"itemId": v["id"], "options": v["options"]})
            for x in v.values():
                visit(x)
        elif isinstance(v, list):
            for x in v:
                visit(x)

    visit(value)
    return items


def record_quiz_answers(rec: Recorder, sources: list[object]) -> None:
    path = OUT / "quiz_answers.json"
    answers: dict[str, dict] = json.loads(path.read_text("utf-8")) if path.exists() else {}
    for src in sources:
        for item in quiz_items(src):
            iid = item["itemId"]
            if iid in answers:
                continue
            opt = item["options"][0]
            chosen = opt.get("id") if isinstance(opt, dict) else opt
            status, body = rec.post_json("/quiz/answer", {"itemId": iid, "chosenId": chosen})
            if status == 200 and isinstance(body, dict):
                answers[iid] = {"answer": body["answer"], "citation": body["citation"]}
    path.write_text(json.dumps(answers, indent=1), "utf-8")
    print(len(answers), "quiz answers", flush=True)


def record_chat(rec: Recorder, rechat: bool) -> None:
    idx_path = OUT / "chat" / "index.json"
    index: list[dict] = json.loads(idx_path.read_text("utf-8")) if idx_path.exists() else []
    done = {e["question"] for e in index}
    turn_re = re.compile(r"turn-[0-9a-f]{12}")
    for n, question in enumerate(CHAT):
        if question in done and not rechat:
            continue
        started = time.perf_counter()
        req = urllib.request.Request(
            BASE + "/chat",
            data=json.dumps({"message": question, "history": []}).encode(),
            headers={"content-type": "application/json", "accept": "text/event-stream"},
        )
        frames: list[dict] = []
        raw = ""
        with urllib.request.urlopen(req, timeout=900) as r:
            buf = ""
            for chunk in iter(lambda: r.read1(4096), b""):
                buf += chunk.decode("utf-8")
                while "\n\n" in buf:
                    frame, buf = buf.split("\n\n", 1)
                    frames.append({"t": round((time.perf_counter() - started) * 1000), "data": frame})
                    raw += frame + "\n\n"
        name = f"chat/{hashlib.sha1(question.encode()).hexdigest()[:12]}.json"
        (OUT / name).write_text(json.dumps({"question": question, "frames": frames}, ensure_ascii=False), "utf-8")
        turns: set[str] = set()
        walk([f["data"] for f in frames], turns, turn_re)
        turns = set(turn_re.findall(raw))
        for tid in turns:
            rec.get(f"/turns/{tid}/trace")
        record_quiz_answers(rec, [json.loads(f["data"][6:]) for f in frames if f["data"].startswith("data: ")])
        index = [e for e in index if e["question"] != question] + [{"question": question, "file": name, "turns": sorted(turns)}]
        idx_path.write_text(json.dumps(index, indent=1, ensure_ascii=False), "utf-8")
        rec.write_index()
        print(f"[{n + 1}/{len(CHAT)}] {round(time.perf_counter() - started)} s, {len(frames)} frames: {question}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-chat", action="store_true")
    ap.add_argument("--only-chat", action="store_true")
    ap.add_argument("--rechat", action="store_true")
    args = ap.parse_args()
    rec = Recorder()
    if not args.only_chat:
        record_views(rec)
    if not args.skip_chat:
        record_chat(rec, args.rechat)
    rec.write_index()
    return 0


if __name__ == "__main__":
    sys.exit(main())
