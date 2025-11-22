# web_app.py
from __future__ import annotations

from typing import Optional, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from todo_agent.config import Settings
from todo_agent.models import SessionState
from todo_agent.planner import propose_todo_list
from todo_agent.executor import run_execution_step
from todo_agent.storage import (
    generate_session_id,
    save_session,
    load_session,
    list_sessions,
)

app = FastAPI(title="Agent-Driven TODO Executor UI")

# Templates & static
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


class CreateSessionRequest(BaseModel):
    goal: str
    mode: Literal["confirm", "auto"] = "confirm"
    model: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Render the main HTML page.
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/sessions")
async def api_list_sessions():
    """
    List existing sessions (lightweight metadata).
    """
    return list_sessions()


@app.post("/api/sessions")
async def api_create_session(body: CreateSessionRequest):
    """
    Create a new session: plan TODO list and save initial state.
    """
    settings = Settings()
    if body.model:
        settings.model = body.model

    state = SessionState(goal=body.goal, mode=body.mode, settings=settings)
    state.log("Session created.")
    state.tasks = propose_todo_list(body.goal, settings)
    state.log(f"Planner created {len(state.tasks)} tasks.")

    session_id = generate_session_id()
    save_session(state, session_id)

    return {
        "session_id": session_id,
        "state": state.to_dict(),
        "has_pending": any(t.status.value == "pending" for t in state.tasks),
    }


@app.get("/api/sessions/{session_id}")
async def api_get_session(session_id: str):
    """
    Get full session state for a given session_id.
    """
    settings = Settings()
    try:
        state = load_session(session_id, settings)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")

    has_pending = any(t.status.value == "pending" for t in state.tasks)
    return {
        "session_id": session_id,
        "state": state.to_dict(),
        "has_pending": has_pending,
    }


@app.post("/api/sessions/{session_id}/execute-step")
async def api_execute_step(session_id: str):
    """
    Execute a single pending task, if any. Returns updated state.
    """
    settings = Settings()
    try:
        state = load_session(session_id, settings)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")

    has_pending_after = run_execution_step(state)
    save_session(state, session_id)

    return {
        "session_id": session_id,
        "state": state.to_dict(),
        "has_pending": has_pending_after,
    }


@app.post("/api/sessions/{session_id}/execute-all")
async def api_execute_all(session_id: str):
    """
    Execute tasks until all are in a terminal state.
    """
    settings = Settings()
    try:
        state = load_session(session_id, settings)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")

    while run_execution_step(state):
        pass

    save_session(state, session_id)

    return {
        "session_id": session_id,
        "state": state.to_dict(),
        "has_pending": False,
    }
