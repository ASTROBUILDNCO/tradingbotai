from __future__ import annotations

import os
from typing import Dict

import httpx

from tools.config_store import load_setting


def _setting(name: str, default: str = "") -> str:
    return str(load_setting(name, os.getenv(name, default)) or "").strip()


def discord_configured() -> bool:
    return bool(_setting("DISCORD_WEBHOOK_URL"))


def dashboard_url(path: str = "/") -> str:
    base = _setting("DASHBOARD_BASE_URL") or _setting("RENDER_EXTERNAL_URL")
    if not base:
        return ""
    base = base.rstrip("/")
    path = path if path.startswith("/") else f"/{path}"
    return f"{base}{path}"


def send_discord_message(content: str) -> Dict[str, str]:
    webhook_url = _setting("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return {"status": "skipped", "reason": "DISCORD_WEBHOOK_URL not configured"}

    safe_content = (content or "").strip()
    if not safe_content:
        return {"status": "skipped", "reason": "empty Discord message"}

    safe_content = safe_content[:1900]

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(webhook_url, json={"content": safe_content})
        if response.status_code >= 400:
            return {"status": "error", "reason": f"Discord HTTP {response.status_code}: {response.text[:250]}"}
        return {"status": "sent", "reason": "Discord webhook accepted the message"}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}
