from __future__ import annotations

import os
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from astro_agent.orchestrator import Orchestrator
from tools.config_store import SECRET_KEYS, save_setting, load_all_masked

app = FastAPI(title="AstroBuild&Co. Beast Agent")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
orchestrator = Orchestrator()
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "change_me_now")


def verify_password(request: Request) -> str:
    password = request.query_params.get("password") or request.headers.get("x-dashboard-password")
    if not password or password != DASHBOARD_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing password")
    return password


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, password: str = Depends(verify_password)):
    return templates.TemplateResponse("dashboard.html", {"request": request, "tasks": orchestrator.approval_queue, "password": password})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, password: str = Depends(verify_password)):
    return templates.TemplateResponse("settings.html", {"request": request, "keys": SECRET_KEYS, "masked": load_all_masked(), "password": password, "saved": request.query_params.get("saved") == "1"})


@app.post("/settings/save")
async def save_settings(request: Request, password: str = Depends(verify_password)):
    form = await request.form()
    for key in SECRET_KEYS:
        value = str(form.get(key, "")).strip()
        if value:
            save_setting(key, value)
    return RedirectResponse(url=f"/settings?password={password}&saved=1", status_code=303)


@app.get("/api/queue")
async def get_queue(password: str = Depends(verify_password)):
    return orchestrator.approval_queue


@app.post("/api/approve/{action_id}")
async def approve_action(action_id: str, password: str = Depends(verify_password)):
    return orchestrator.approve_action(action_id)


@app.post("/api/skip/{action_id}")
async def skip_action(action_id: str, password: str = Depends(verify_password)):
    return orchestrator.skip_action(action_id)


@app.post("/api/run/{routine}")
async def run_routine(routine: str, password: str = Depends(verify_password)):
    routine = routine.lower()
    if routine == "morning":
        orchestrator.run_morning_routine()
    elif routine == "midday":
        orchestrator.run_midday_routine()
    elif routine == "evening":
        orchestrator.run_evening_routine()
    elif routine == "check_email":
        orchestrator.check_email()
    elif routine == "draft_facebook_post":
        orchestrator.draft_facebook_post()
    elif routine == "approval_queue":
        pass
    else:
        raise HTTPException(status_code=400, detail="Unknown routine")
    return {"status": "triggered", "routine": routine, "pending_actions": len(orchestrator.approval_queue)}


@app.get("/health")
async def health():
    return {"ok": True, "service": "AstroBuild&Co. Beast Agent"}
