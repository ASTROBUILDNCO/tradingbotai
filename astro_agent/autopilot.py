from __future__ import annotations

import os
import threading
import time
from datetime import datetime
from typing import Dict
from zoneinfo import ZoneInfo

from tools.config_store import load_setting

_started = False
_state: Dict[str, str] = {
    "enabled": "unknown",
    "last_tick": "never",
    "last_email_scan": "never",
    "last_error": "",
    "mode": "draft-only autopilot",
}


def _truthy(value: str) -> bool:
    return str(value).strip().lower() not in {"0", "false", "off", "no", "disabled"}


def autopilot_status() -> Dict[str, str]:
    return dict(_state)


def _now_local() -> datetime:
    tz_name = load_setting("TIMEZONE", "America/New_York") or "America/New_York"
    try:
        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        return datetime.now(ZoneInfo("America/New_York"))


def _email_ready() -> bool:
    return all(bool(load_setting(k, "")) for k in ["IMAP_HOST", "IMAP_PORT", "IMAP_USER", "IMAP_PASSWORD"])


def run_autopilot_once(orchestrator, force: bool = False) -> Dict[str, str]:
    now = _now_local()
    stamp = now.strftime("%Y-%m-%d %H:%M:%S %Z")
    _state["enabled"] = "true"
    _state["last_tick"] = stamp
    _state["email_ready"] = "true" if _email_ready() else "false"
    actions = []

    try:
        today = now.strftime("%Y-%m-%d")
        hour = now.hour

        if force and _email_ready():
            orchestrator.check_email()
            _state["last_email_scan"] = stamp
            actions.append("email scan")
        elif force:
            actions.append("email not connected")

        if hour >= 8 and _state.get("morning_date") != today:
            orchestrator.run_morning_routine()
            _state["morning_date"] = today
            actions.append("morning routine")

        if hour >= 12 and _state.get("midday_date") != today:
            orchestrator.run_midday_routine()
            _state["midday_date"] = today
            actions.append("midday routine")

        if hour >= 18 and _state.get("evening_date") != today:
            orchestrator.run_evening_routine()
            _state["evening_date"] = today
            actions.append("evening routine")

        email_minutes = int(os.getenv("AUTOPILOT_EMAIL_MINUTES", "20"))
        last_scan_epoch = float(_state.get("last_email_scan_epoch", "0") or "0")
        if _email_ready() and (force or time.time() - last_scan_epoch >= email_minutes * 60):
            orchestrator.check_email()
            _state["last_email_scan"] = stamp
            _state["last_email_scan_epoch"] = str(time.time())
            actions.append("email scan")

        _state["last_error"] = ""
        return {"status": "ok", "actions": ", ".join(actions) or "none", "time": stamp}
    except Exception as exc:
        _state["last_error"] = str(exc)
        return {"status": "error", "error": str(exc), "time": stamp}


def _loop(orchestrator) -> None:
    while True:
        run_autopilot_once(orchestrator)
        time.sleep(int(os.getenv("AUTOPILOT_TICK_SECONDS", "300")))


def start_autopilot(orchestrator) -> None:
    global _started
    enabled = _truthy(os.getenv("AUTOPILOT_ENABLED", "true"))
    _state["enabled"] = "true" if enabled else "false"
    if not enabled or _started:
        return
    _started = True
    thread = threading.Thread(target=_loop, args=(orchestrator,), daemon=True)
    thread.start()
