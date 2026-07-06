import uuid
import subprocess
import threading
import traceback
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

WATCHTOWER_DIR = Path(__file__).resolve().parent.parent


def _venv_python(base: Path) -> Path:
    """Locate the project venv's Python across OSes (Windows Scripts/, else
    bin/), falling back to whatever interpreter is running this server."""
    win = base / "venv" / "Scripts" / "python.exe"
    nix = base / "venv" / "bin" / "python"
    if win.exists():
        return win
    if nix.exists():
        return nix
    return Path(sys.executable)


WATCHTOWER_PYTHON = _venv_python(WATCHTOWER_DIR)
WATCHTOWER_OUTPUT = WATCHTOWER_DIR / "output"
PIPELINES_DIR = WATCHTOWER_OUTPUT / "pipelines"
WATCHTOWER_OUTPUT.mkdir(parents=True, exist_ok=True)

# State machine: (command, current_stage, action) -> next stage
# Use "__complete__" to mark final state without spawning a subprocess.
import threading as _threading_mod
_STATE_LOCKS = {}
_STATE_LOCKS_GUARD = _threading_mod.Lock()


def _get_lock(pipeline_id: str) -> _threading_mod.Lock:
    with _STATE_LOCKS_GUARD:
        lock = _STATE_LOCKS.get(pipeline_id)
        if lock is None:
            lock = _threading_mod.Lock()
            _STATE_LOCKS[pipeline_id] = lock
        return lock


TRANSITIONS = {
    # ideate
    ("ideate", None, "start"):                  "fetch",
    ("ideate", "review_polls", "approve"):      "build",
    ("ideate", "review_polls", "regenerate"):   "regenerate",
    ("ideate", "review_polls", "edit"):         "build",

    # poll
    ("poll",   None, "start"):                  "generate",
    ("poll",   "review_poll", "approve"):       "build",
    ("poll",   "review_poll", "regenerate"):    "regenerate",
    ("poll",   "review_poll", "edit"):          "build",

    # run (Weekly Comics)
    ("run",    None, "start"):                  "fetch",
    ("run",    "review_picks", "approve"):      "build",
    ("run",    "review_carousel", "approve"):     "__complete__",
    ("run",    "review_carousel", "edit"):        "__complete__",
    ("run",    "review_carousel", "regenerate"):  "regenerate_caption",

    # movies
    ("movies", None, "start"):                  "fetch",
    ("movies", "review_picks", "approve"):      "build",
    ("movies", "review_carousel", "approve"):     "__complete__",
    ("movies", "review_carousel", "edit"):        "__complete__",
    ("movies", "review_carousel", "regenerate"):  "regenerate_caption",

    # tv
    ("tv",     None, "start"):                  "fetch",
    ("tv",     "review_picks", "approve"):      "build",
    ("tv",     "review_carousel", "approve"):     "__complete__",
    ("tv",     "review_carousel", "edit"):        "__complete__",
    ("tv",     "review_carousel", "regenerate"):  "regenerate_caption",

    # games
    ("games",  None, "start"):                  "fetch",
    ("games",  "review_picks", "approve"):      "build",
    ("games",  "review_carousel", "approve"):     "__complete__",
    ("games",  "review_carousel", "edit"):        "__complete__",
    ("games",  "review_carousel", "regenerate"):  "regenerate_caption",

    # review (book review)
    ("review", None, "start"):                  "draft",
    ("review", "review_draft", "approve"):      "build",
    ("review", "review_draft", "edit"):         "build",
    ("review", "review_draft", "regenerate"):   "draft",
    ("review", "review_caption", "approve"):    "save",
    ("review", "review_caption", "edit"):       "save",
    ("review", "review_caption", "regenerate"): "regenerate_caption",
}


app = FastAPI(title="WatchTower Pipeline API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Serve generated slides and any output files so the iPhone can render them.
app.mount("/files", StaticFiles(directory=str(WATCHTOWER_OUTPUT)), name="files")


class StartBody(BaseModel):
    payload: dict | None = None


class DecideBody(BaseModel):
    action: str
    payload: dict | None = None


def _state_path(pipeline_id: str) -> Path:
    return PIPELINES_DIR / f"{pipeline_id}.json"


def _load_state(pipeline_id: str) -> dict | None:
    p = _state_path(pipeline_id)
    if not p.exists():
        return None
    with _get_lock(pipeline_id):
        text = p.read_text(encoding="utf-8")
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _save_state(pipeline_id: str, state: dict):
    p = _state_path(pipeline_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, indent=2, default=str)
    with _get_lock(pipeline_id):
        p.write_text(payload, encoding="utf-8")


def _append_log(pipeline_id: str, line: str):
    state = _load_state(pipeline_id)
    if not state:
        return
    state.setdefault("log", []).append(line)
    state["updated_at"] = datetime.utcnow().isoformat()
    _save_state(pipeline_id, state)


def _to_public_url(file_path: str) -> str | None:
    """Convert a local output path to a /files/... URL.
    Relative paths are resolved against WATCHTOWER_DIR (since the subprocess CWD is WatchTower)."""
    try:
        p = Path(file_path)
        if not p.is_absolute():
            p = (WATCHTOWER_DIR / p).resolve()
        else:
            p = p.resolve()
        rel = p.relative_to(WATCHTOWER_OUTPUT.resolve())
        # URL-encode each path segment to handle spaces/unicode safely
        from urllib.parse import quote
        parts = [quote(part) for part in str(rel).replace("\\", "/").split("/")]
        return "/files/" + "/".join(parts)
    except (ValueError, OSError):
        return None


def _publicize_artifact_paths(state: dict):
    """For slides arrays in current_artifact, swap local paths for /files URLs."""
    art = state.get("current_artifact") or {}
    if "slides" in art and isinstance(art["slides"], list):
        art["slides_urls"] = [_to_public_url(s) for s in art["slides"]]
    if "slide_path" in art and isinstance(art["slide_path"], str):
        art["slide_url"] = _to_public_url(art["slide_path"])


def _run_stage(pipeline_id: str, command: str, stage_name: str):
    try:
        state = _load_state(pipeline_id) or {"command": command, "data": {}, "log": []}
        state["status"] = "running_stage"
        state["stage"] = stage_name
        state["updated_at"] = datetime.utcnow().isoformat()
        _save_state(pipeline_id, state)

        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        cmd = [str(WATCHTOWER_PYTHON), "-m", "app", "stage", command, stage_name,
               "--state-file", str(_state_path(pipeline_id))]
        _append_log(pipeline_id, f"[api] Spawning: {' '.join(cmd)}")

        proc = subprocess.Popen(
            cmd,
            cwd=str(WATCHTOWER_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            encoding="utf-8",
            errors="replace",
        )

        stdout = proc.stdout
        assert stdout is not None
        for line in iter(stdout.readline, ''):
            line = line.rstrip()
            if line:
                _append_log(pipeline_id, line)
        proc.wait()

        state = _load_state(pipeline_id) or state
        if proc.returncode != 0:
            state["status"] = "failed"
            state.setdefault("error", f"Stage subprocess exited {proc.returncode}")
        # Publicize paths so the iPhone can load slide images
        _publicize_artifact_paths(state)
        state["updated_at"] = datetime.utcnow().isoformat()
        _save_state(pipeline_id, state)

    except Exception:
        tb = traceback.format_exc()
        try:
            state = _load_state(pipeline_id) or {"command": command, "data": {}, "log": []}
            state["status"] = "failed"
            state["error"] = "Thread crashed in _run_stage"
            state.setdefault("log", []).append("[api] THREAD CRASH:")
            for line in tb.splitlines():
                state["log"].append(line)
            state["updated_at"] = datetime.utcnow().isoformat()
            _save_state(pipeline_id, state)
        except Exception:
            pass


@app.get("/")
def root():
    return {"service": "WatchTower Pipeline API", "status": "ok"}


@app.post("/pipelines/{command}")
def start_pipeline(command: str, body: StartBody | None = None):
    first_stage = TRANSITIONS.get((command, None, "start"))
    if not first_stage:
        raise HTTPException(status_code=400, detail=f"Unknown command: {command}")

    pipeline_id = str(uuid.uuid4())[:8]
    state = {
        "id": pipeline_id,
        "command": command,
        "stage": "init",
        "status": "running_stage",
        "data": (body.payload if body and body.payload else {}),
        "log": [],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    _save_state(pipeline_id, state)

    threading.Thread(target=_run_stage, args=(pipeline_id, command, first_stage), daemon=True).start()
    return {"pipeline_id": pipeline_id, "status": "running_stage"}


@app.get("/pipelines/{pipeline_id}")
def get_pipeline(pipeline_id: str):
    state = _load_state(pipeline_id)
    if not state:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    state["id"] = pipeline_id
    return state


@app.post("/pipelines/{pipeline_id}/decide")
def decide(pipeline_id: str, body: DecideBody):
    state = _load_state(pipeline_id)
    if not state:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    command = state["command"]
    current_stage = state.get("stage")
    action = body.action

    current_actions = (state.get("current_artifact") or {}).get("actions", [])
    if action not in current_actions:
        raise HTTPException(status_code=400, detail=f"Action '{action}' not allowed. Allowed: {current_actions}")

    # Merge any payload into state.data so the next stage sees it
    if body.payload:
        state.setdefault("data", {}).update(body.payload)
        _save_state(pipeline_id, state)

    next_stage = TRANSITIONS.get((command, current_stage, action))
    if not next_stage:
        raise HTTPException(status_code=400, detail=f"No transition from {current_stage} via {action}")

    # In-memory completion (no subprocess)
    if next_stage == "__complete__":
        state["status"] = "complete"
        state["stage"] = "complete"
        if state.get("current_artifact"):
            state["current_artifact"]["actions"] = []
        state["updated_at"] = datetime.utcnow().isoformat()
        _publicize_artifact_paths(state)
        _save_state(pipeline_id, state)
        return {"pipeline_id": pipeline_id, "status": "complete"}

    threading.Thread(target=_run_stage, args=(pipeline_id, command, next_stage), daemon=True).start()
    return {"pipeline_id": pipeline_id, "status": "running_stage", "next_stage": next_stage}


@app.get("/pipelines")
def list_pipelines():
    if not PIPELINES_DIR.exists():
        return {"pipelines": []}
    out = []
    for f in sorted(PIPELINES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            s = json.loads(f.read_text(encoding="utf-8"))
            out.append({
                "id": f.stem,
                "command": s.get("command"),
                "stage": s.get("stage"),
                "status": s.get("status"),
                "updated_at": s.get("updated_at"),
            })
        except Exception:
            continue
    return {"pipelines": out}


@app.delete("/pipelines/{pipeline_id}")
def delete_pipeline(pipeline_id: str):
    p = _state_path(pipeline_id)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Pipeline not found")
    p.unlink()
    return {"deleted": pipeline_id}