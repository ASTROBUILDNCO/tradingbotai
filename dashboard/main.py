from __future__ import annotations

import os
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from astro_agent.autopilot import autopilot_status, run_autopilot_once, start_autopilot
from astro_agent.orchestrator import Orchestrator
from tools.config_store import SECRET_KEYS, save_setting, load_all_masked
from tools.workflow_store import add_opportunity, archive_opportunity, dashboard_snapshot, update_opportunity
from tools.seed_interest_store import catalog, lead_counts, leads_csv, list_drop_list, list_inquiries, save_drop_list, save_inquiry

app = FastAPI(title="AstroBuild&Co. Beast Agent")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
orchestrator = Orchestrator()
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "change_me_now")
SEED_BRAND_NAME = os.getenv("SEED_BRAND_NAME", "Astro Genetics")
SOLANA_PAYMENT_WALLET = os.getenv("SOLANA_PAYMENT_WALLET", "C7iQe8hdyGXGVE62NxJWQXPim4sfcNNHPUugiX57qUxv")


@app.on_event("startup")
async def startup_event():
    start_autopilot(orchestrator)


def verify_password(request: Request) -> str:
    password = request.query_params.get("password") or request.headers.get("x-dashboard-password")
    if not password or password != DASHBOARD_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing password")
    return password


def _seed_context(request: Request):
    return {
        "request": request,
        "brand_name": SEED_BRAND_NAME,
        "catalog": catalog(),
        "solana_wallet": SOLANA_PAYMENT_WALLET,
        "saved": request.query_params.get("saved") in {"1", "waitlist", "inquiry"},
    }


def _money(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value or "").replace("$", "").replace(",", "").strip() or default)
    except Exception:
        return default


def _save_quick_quote_to_tracker(form) -> None:
    job_name = str(form.get("job_name", "")).strip()
    if not job_name:
        return

    hours = _money(form.get("labor_hours"))
    rate = _money(form.get("labor_rate"), 75.0)
    materials = _money(form.get("materials"))
    travel = _money(form.get("travel"))
    rental = _money(form.get("rental"))
    margin_pct = _money(form.get("margin"), 20.0)
    cost = (hours * rate) + materials + travel + rental
    price = cost / (1 - (margin_pct / 100)) if margin_pct < 95 else cost * 1.25
    profit = price - cost

    add_opportunity({
        "title": job_name,
        "source": "Quick Quote",
        "status": "quote_draft",
        "price": price,
        "cost": cost,
        "profit": profit,
        "probability": 45,
        "fit_score": 70,
        "next_action": "Verify scope, access, materials, wage/rental risk, due date, and submission path before sending.",
        "notes": (
            f"Quick quote math saved from dashboard.\n"
            f"Labor: {hours:.1f} hrs x ${rate:.2f}/hr\n"
            f"Materials: ${materials:,.2f}\n"
            f"Travel: ${travel:,.2f}\n"
            f"Rental/tools: ${rental:,.2f}\n"
            f"Margin target: {margin_pct:.1f}%"
        ),
    })


@app.get("/seeds", response_class=HTMLResponse)
async def seed_brand(request: Request):
    return templates.TemplateResponse("seed_brand.html", _seed_context(request))


@app.get("/astrogenetics", response_class=HTMLResponse)
async def astro_genetics(request: Request):
    return templates.TemplateResponse("seed_brand.html", _seed_context(request))


@app.get("/astro-genetics", response_class=HTMLResponse)
async def astro_genetics_dash(request: Request):
    return RedirectResponse(url="/astrogenetics", status_code=302)


@app.post("/seeds/waitlist")
async def seed_waitlist(request: Request):
    form = await request.form()
    save_drop_list(form)
    return RedirectResponse(url="/astrogenetics?saved=waitlist", status_code=303)


@app.post("/seeds/inquiry")
async def seed_inquiry(request: Request):
    form = await request.form()
    save_inquiry(form)
    return RedirectResponse(url="/astrogenetics?saved=inquiry", status_code=303)


@app.get("/seeds/admin", response_class=HTMLResponse)
async def seed_admin(request: Request, password: str = Depends(verify_password)):
    return templates.TemplateResponse(
        "seed_admin.html",
        {
            "request": request,
            "password": password,
            "counts": lead_counts(),
            "drop_list": list_drop_list(),
            "inquiries": list_inquiries(),
        },
    )


@app.get("/seeds/admin/export")
async def seed_admin_export(password: str = Depends(verify_password)):
    return Response(
        content=leads_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=seed-interest-leads.csv"},
    )


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, password: str = Depends(verify_password)):
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "tasks": orchestrator.approval_queue,
            "password": password,
            "autopilot": autopilot_status(),
            "workflow": dashboard_snapshot(),
        },
    )


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


@app.get("/api/workflow")
async def get_workflow(password: str = Depends(verify_password)):
    return dashboard_snapshot()


@app.post("/api/opportunities/add")
async def add_opportunity_route(request: Request, password: str = Depends(verify_password)):
    form = await request.form()
    add_opportunity({
        "title": form.get("title"),
        "source": form.get("source"),
        "agency": form.get("agency"),
        "contact": form.get("contact"),
        "due_at": form.get("due_at"),
        "status": form.get("status") or "lead",
        "price": form.get("price"),
        "cost": form.get("cost"),
        "profit": form.get("profit"),
        "probability": form.get("probability"),
        "fit_score": form.get("fit_score"),
        "next_action": form.get("next_action"),
        "next_follow_up": form.get("next_follow_up"),
        "notes": form.get("notes"),
    })
    return RedirectResponse(url=f"/?password={password}", status_code=303)


@app.post("/api/opportunities/{opportunity_id}/update")
async def update_opportunity_route(opportunity_id: str, request: Request, password: str = Depends(verify_password)):
    form = await request.form()
    update_opportunity(opportunity_id, {
        "status": form.get("status"),
        "next_action": form.get("next_action"),
        "next_follow_up": form.get("next_follow_up"),
        "price": form.get("price"),
        "cost": form.get("cost"),
        "profit": form.get("profit"),
        "probability": form.get("probability"),
        "fit_score": form.get("fit_score"),
        "notes": form.get("notes"),
    })
    return RedirectResponse(url=f"/?password={password}", status_code=303)


@app.post("/api/opportunities/{opportunity_id}/archive")
async def archive_opportunity_route(opportunity_id: str, password: str = Depends(verify_password)):
    archive_opportunity(opportunity_id)
    return RedirectResponse(url=f"/?password={password}", status_code=303)


@app.get("/api/autopilot/status")
async def get_autopilot_status(password: str = Depends(verify_password)):
    return autopilot_status()


@app.post("/api/autopilot/tick")
async def autopilot_tick(password: str = Depends(verify_password)):
    run_autopilot_once(orchestrator, force=True)
    return RedirectResponse(url=f"/?password={password}", status_code=303)


@app.post("/api/discord/test")
async def discord_test(password: str = Depends(verify_password)):
    orchestrator.send_discord_test()
    return RedirectResponse(url=f"/?password={password}", status_code=303)


@app.post("/api/approve/{action_id}")
async def approve_action(action_id: str, password: str = Depends(verify_password)):
    orchestrator.approve_action(action_id)
    return RedirectResponse(url=f"/?password={password}", status_code=303)


@app.post("/api/skip/{action_id}")
async def skip_action(action_id: str, password: str = Depends(verify_password)):
    orchestrator.skip_action(action_id)
    return RedirectResponse(url=f"/?password={password}", status_code=303)


@app.post("/api/quick/paste")
async def quick_paste(request: Request, password: str = Depends(verify_password)):
    form = await request.form()
    orchestrator.analyze_pasted_message(str(form.get("message", "")))
    return RedirectResponse(url=f"/?password={password}", status_code=303)


@app.post("/api/quick/quote")
async def quick_quote(request: Request, password: str = Depends(verify_password)):
    form = await request.form()
    orchestrator.build_quick_quote(str(form.get("job_name", "Quick job")), str(form.get("labor_hours", "")), str(form.get("labor_rate", "")), str(form.get("materials", "")), str(form.get("travel", "")), str(form.get("rental", "")), str(form.get("margin", "")))
    _save_quick_quote_to_tracker(form)
    return RedirectResponse(url=f"/?password={password}", status_code=303)


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
    elif routine == "find_leads":
        orchestrator.run_lead_finder()
    elif routine == "approval_queue":
        pass
    else:
        raise HTTPException(status_code=400, detail="Unknown routine")
    return RedirectResponse(url=f"/?password={password}", status_code=303)


@app.get("/health")
async def health():
    snap = dashboard_snapshot()
    seed_counts = lead_counts()
    return {"ok": True, "service": "AstroBuild&Co. Beast Agent", "autopilot": autopilot_status(), "workflow_active": snap["summary"]["active"], "seed_interest_total": seed_counts["total"]}
