from __future__ import annotations

import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from astro_agent.orchestrator import Orchestrator
from tools.config_store import SECRET_KEYS, save_setting, load_all_masked

app = FastAPI(title="AstroBuild&Co. Beast Agent")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
orchestrator = Orchestrator()


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "tasks": orchestrator.approval_queue, "password": ""})


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request, "keys": SECRET_KEYS, "masked": load_all_masked(), "password": "", "saved": request.query_params.get("saved") == "1"})


@app.post("/settings/save")
async def save_settings(request: Request):
    form = await request.form()
    for key in SECRET_KEYS:
        value = str(form.get(key, "")).strip()
        if value:
            save_setting(key, value)
    return RedirectResponse(url="/settings?saved=1", status_code=303)


@app.get("/api/queue")
async def get_queue():
    return orchestrator.approval_queue


@app.post("/api/approve/{action_id}")
async def approve_action(action_id: str):
    return orchestrator.approve_action(action_id)


@app.post("/api/skip/{action_id}")
async def skip_action(action_id: str):
    return orchestrator.skip_action(action_id)


@app.post("/api/quick/paste")
async def quick_paste(request: Request):
    form = await request.form()
    orchestrator.analyze_pasted_message(str(form.get("message", "")))
    return RedirectResponse(url="/", status_code=303)


@app.post("/api/quick/quote")
async def quick_quote(request: Request):
    form = await request.form()
    orchestrator.build_quick_quote(
        str(form.get("job_name", "Quick job")),
        str(form.get("labor_hours", "")),
        str(form.get("labor_rate", "")),
        str(form.get("materials", "")),
        str(form.get("travel", "")),
        str(form.get("rental", "")),
        str(form.get("margin", "")),
    )
    return RedirectResponse(url="/", status_code=303)


@app.post("/api/run/{routine}")
async def run_routine(routine: str):
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
    return RedirectResponse(url="/", status_code=303)


@app.get("/health")
async def health():
    return {"ok": True, "service": "AstroBuild&Co. Beast Agent"}
