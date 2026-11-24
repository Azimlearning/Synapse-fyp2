"""Record the simulation engine's (genui/) real responses for the hosted demo (genui/web/demo-data/).

Run the simulation API in library mode, which makes no model call and costs nothing:

    cd genui && SYNAPSE_LLM_MODE=fake PUBLIC_ORIGIN=http://localhost:3001 uv run uvicorn api.main:app --port 8001
    uv run python demo/record/record_simulations.py

It saves the library list, every stored Environment (with its translations and export), the Kit files under /vendor/kit, and
the /ask stream of every question the library answers word for word. The replay route (genui/web/app/demo-api/[...path]/route.ts)
rewrites http://localhost:3001 to the deployed origin, because each Environment's CSP names the origin its Kit is served from.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BASE = "http://localhost:8001"
OUT = REPO / "genui" / "web" / "demo-data"
KIT_DIST = REPO / "genui" / "packages" / "kit" / "dist"

# Questions asked by the Synapse app's simulation picker (web/components/shell/SimulationDrawer.tsx) and the engine's own quick starts.
EXTRA_QUESTIONS = [
    "Why does a spring stretch when I hang a weight on it?",
    "What happens to the current if I raise the resistance in a circuit?",
    "How does the pressure change as a diver goes deeper in water?",
    "How much would I weigh on Jupiter compared with Earth?",
    "How does a black hole bend light?",
    "How does the length of a pendulum change how long each swing takes?",
    "How does reciprocal rank fusion merge a keyword search ranking and a vector search ranking into one list?",
    "How does the size of a text chunk change whether retrieval finds the right passage?",
    "How does following links in a knowledge graph find an answer that is two hops away from the question?",
    "How do I find the concentration of an acid by titration?",
    "Why does yeast make limewater go milky?",
    "What is Newton's cannonball, and how does a satellite stay in orbit?",
    "What happens to the pitch of an ambulance siren as it drives past?",
    "How much electrical energy does a lamp use?",
]


def fetch(path: str, method: str = "GET", body: dict | None = None) -> tuple[int, bytes, str]:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"content-type": "application/json"} if body is not None else {}
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, r.read(), r.headers.get("content-type", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get("content-type", "")


def main() -> int:
    (OUT / "get").mkdir(parents=True, exist_ok=True)
    (OUT / "ask").mkdir(parents=True, exist_ok=True)
    routes: dict[str, dict] = {}

    def save(path: str) -> bytes:
        status, body, ctype = fetch(path)
        name = hashlib.sha1(path.encode()).hexdigest()[:16] + (".json" if "json" in ctype else ".bin")
        (OUT / "get" / name).write_bytes(body)
        routes[f"GET {path}"] = {"status": status, "file": f"get/{name}", "type": ctype or "application/json"}
        return body

    save("/health")
    lib = json.loads(save("/library"))
    for env in lib["environments"]:
        eid = urllib.parse.quote(env["id"], safe="")
        save(f"/library/{eid}")
        save(f"/library/{eid}/translations")
        save(f"/library/{eid}/export")
        print("env", env["id"], flush=True)

    known = json.loads((REPO / "genui" / "data" / "library_questions.json").read_text("utf-8"))
    questions = [q for k, qs in known.items() if not k.startswith("_") for q in qs] + EXTRA_QUESTIONS
    index = []
    for q in dict.fromkeys(questions):
        started = time.perf_counter()
        req = urllib.request.Request(
            BASE + "/ask", data=json.dumps({"question": q}).encode(),
            headers={"content-type": "application/json", "accept": "text/event-stream"},
        )
        frames = []
        with urllib.request.urlopen(req, timeout=300) as r:
            buf = ""
            for chunk in iter(lambda: r.read1(4096), b""):
                buf += chunk.decode("utf-8")
                while "\n\n" in buf:
                    frame, buf = buf.split("\n\n", 1)
                    frames.append({"t": round((time.perf_counter() - started) * 1000), "data": frame})
        text = "\n".join(f["data"] for f in frames)
        # Only a question the library answered is replayed; anything the demo model made up is left out.
        if '"layer":"library"' not in text or '"type":"environment"' not in text:
            print("not in the library, skipped:", q, flush=True)
            continue
        name = f"ask/{hashlib.sha1(q.encode()).hexdigest()[:12]}.json"
        (OUT / name).write_text(json.dumps({"question": q, "frames": frames}, ensure_ascii=False), "utf-8")
        index.append({"question": q, "file": name})
        print("ask", len(frames), "frames:", q, flush=True)

    (OUT / "ask" / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False), "utf-8")
    (OUT / "routes.json").write_text(json.dumps(routes, indent=1, sort_keys=True), "utf-8")

    vendor = OUT / "vendor" / "kit"
    if vendor.exists():
        shutil.rmtree(vendor)
    shutil.copytree(KIT_DIST, vendor)
    print(len(routes), "routes,", len(index), "questions, Kit copied", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
