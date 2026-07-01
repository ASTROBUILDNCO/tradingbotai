from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

DB_PATH = Path(os.getenv("WORKFLOW_DB_PATH", os.getenv("CONFIG_DB_PATH", "data/astro_config.sqlite3")).replace("astro_config", "astro_workflow"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today() -> date:
    return date.today()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS opportunities (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            source TEXT DEFAULT '',
            agency TEXT DEFAULT '',
            contact TEXT DEFAULT '',
            due_at TEXT DEFAULT '',
            status TEXT DEFAULT 'lead',
            price REAL DEFAULT 0,
            cost REAL DEFAULT 0,
            profit REAL DEFAULT 0,
            probability INTEGER DEFAULT 50,
            fit_score INTEGER DEFAULT 50,
            next_action TEXT DEFAULT '',
            next_follow_up TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS activity (
            id TEXT PRIMARY KEY,
            opportunity_id TEXT DEFAULT '',
            kind TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    return conn


def _money(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value or "").replace("$", "").replace(",", "").strip() or default)
    except Exception:
        return default


def _int(value: object, default: int = 50) -> int:
    try:
        return max(0, min(100, int(float(str(value or "").strip() or default))))
    except Exception:
        return default


def _clean(value: object, limit: int = 2000) -> str:
    return str(value or "").strip()[:limit]


def init_db() -> None:
    with _conn():
        pass


def add_activity(kind: str, body: str, opportunity_id: str = "") -> str:
    activity_id = str(uuid.uuid4())
    with _conn() as conn:
        conn.execute(
            "INSERT INTO activity (id, opportunity_id, kind, body, created_at) VALUES (?, ?, ?, ?, ?)",
            (activity_id, opportunity_id, _clean(kind, 50), _clean(body, 2000), _now()),
        )
    return activity_id


def add_opportunity(data: Dict[str, object]) -> str:
    opportunity_id = str(uuid.uuid4())
    price = _money(data.get("price"))
    cost = _money(data.get("cost"))
    profit = _money(data.get("profit"), price - cost if price or cost else 0.0)
    now = _now()
    title = _clean(data.get("title") or data.get("job_name") or "Untitled opportunity", 180)
    status = _clean(data.get("status") or "lead", 50)
    next_action = _clean(data.get("next_action") or "Decide: chase, quote, follow up, or kill it.", 500)
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO opportunities (
                id, title, source, agency, contact, due_at, status, price, cost, profit,
                probability, fit_score, next_action, next_follow_up, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                opportunity_id,
                title,
                _clean(data.get("source"), 120),
                _clean(data.get("agency"), 180),
                _clean(data.get("contact"), 220),
                _clean(data.get("due_at"), 80),
                status,
                price,
                cost,
                profit,
                _int(data.get("probability"), 50),
                _int(data.get("fit_score"), 50),
                next_action,
                _clean(data.get("next_follow_up"), 80),
                _clean(data.get("notes"), 2000),
                now,
                now,
            ),
        )
    add_activity("opportunity_added", f"{title} added as {status}", opportunity_id)
    return opportunity_id


def update_opportunity(opportunity_id: str, data: Dict[str, object]) -> bool:
    allowed = {
        "title": 180,
        "source": 120,
        "agency": 180,
        "contact": 220,
        "due_at": 80,
        "status": 50,
        "next_action": 500,
        "next_follow_up": 80,
        "notes": 2000,
    }
    assignments: List[str] = []
    values: List[object] = []

    for key, limit in allowed.items():
        if key in data:
            assignments.append(f"{key} = ?")
            values.append(_clean(data.get(key), limit))

    for key in ["price", "cost", "profit"]:
        if key in data:
            assignments.append(f"{key} = ?")
            values.append(_money(data.get(key)))

    for key in ["probability", "fit_score"]:
        if key in data:
            assignments.append(f"{key} = ?")
            values.append(_int(data.get(key), 50))

    if not assignments:
        return False

    assignments.append("updated_at = ?")
    values.append(_now())
    values.append(opportunity_id)

    with _conn() as conn:
        cur = conn.execute(f"UPDATE opportunities SET {', '.join(assignments)} WHERE id = ?", values)
    if cur.rowcount:
        add_activity("opportunity_updated", f"Updated opportunity {opportunity_id}", opportunity_id)
    return bool(cur.rowcount)


def archive_opportunity(opportunity_id: str) -> bool:
    return update_opportunity(opportunity_id, {"status": "archived", "next_action": "Archived / hidden from active board."})


def _money_fmt(value: object) -> str:
    return f"${_money(value):,.0f}"


def _row_to_dict(row: sqlite3.Row) -> Dict[str, object]:
    out = dict(row)
    out["price"] = float(out.get("price") or 0)
    out["cost"] = float(out.get("cost") or 0)
    out["profit"] = float(out.get("profit") or 0)
    out["probability"] = int(out.get("probability") or 0)
    out["fit_score"] = int(out.get("fit_score") or 0)
    out["price_display"] = _money_fmt(out.get("price"))
    out["cost_display"] = _money_fmt(out.get("cost"))
    out["profit_display"] = _money_fmt(out.get("profit"))
    return out


def list_opportunities(include_archived: bool = False, limit: int = 100) -> List[Dict[str, object]]:
    where = "" if include_archived else "WHERE status != 'archived'"
    with _conn() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM opportunities
            {where}
            ORDER BY
                CASE WHEN next_follow_up != '' THEN 0 ELSE 1 END,
                next_follow_up ASC,
                CASE WHEN due_at != '' THEN 0 ELSE 1 END,
                due_at ASC,
                updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _parse_date(value: object) -> Optional[date]:
    text = _clean(value, 40)
    if not text:
        return None
    for candidate in [text[:10], text]:
        try:
            return datetime.fromisoformat(candidate).date()
        except Exception:
            pass
    return None


def dashboard_snapshot() -> Dict[str, object]:
    init_db()
    opportunities = list_opportunities()
    today = _today()
    soon = today + timedelta(days=3)

    due_soon: List[Dict[str, object]] = []
    followups_due: List[Dict[str, object]] = []
    submitted: List[Dict[str, object]] = []
    quote_work: List[Dict[str, object]] = []
    leads: List[Dict[str, object]] = []

    for opp in opportunities:
        due_date = _parse_date(opp.get("due_at"))
        follow_date = _parse_date(opp.get("next_follow_up"))
        status = str(opp.get("status") or "").lower()

        if due_date and due_date <= soon and status not in {"lost", "won", "archived"}:
            due_soon.append(opp)
        if follow_date and follow_date <= today and status not in {"lost", "won", "archived"}:
            followups_due.append(opp)
        if status in {"submitted", "waiting", "awaiting_response"}:
            submitted.append(opp)
        if status in {"lead", "reviewing", "quote_draft", "pricing"}:
            quote_work.append(opp)
        if status == "lead":
            leads.append(opp)

    expected_pipeline = sum(float(opp.get("profit") or 0) * (int(opp.get("probability") or 0) / 100) for opp in opportunities)
    open_profit = sum(float(opp.get("profit") or 0) for opp in opportunities)

    today_moves: List[Dict[str, str]] = []
    for opp in followups_due[:3]:
        today_moves.append({
            "label": "Follow up now",
            "title": str(opp.get("title", "")),
            "detail": str(opp.get("next_action") or "Send a clean status follow-up."),
        })
    for opp in due_soon[:3]:
        today_moves.append({
            "label": "Deadline close",
            "title": str(opp.get("title", "")),
            "detail": f"Due {opp.get('due_at')}. Finish price, docs, and submission path.",
        })
    if not today_moves and opportunities:
        best = sorted(opportunities, key=lambda item: (int(item.get("fit_score") or 0), float(item.get("profit") or 0)), reverse=True)[0]
        today_moves.append({
            "label": "Best money move",
            "title": str(best.get("title", "")),
            "detail": str(best.get("next_action") or "Push this one forward or kill it."),
        })
    if not today_moves:
        today_moves.append({
            "label": "Start here",
            "title": "Add the first live opportunity",
            "detail": "Put Kittyhawk, a SAM RFQ, a local lead, or a customer follow-up into the tracker.",
        })

    return {
        "opportunities": opportunities,
        "due_soon": due_soon,
        "followups_due": followups_due,
        "submitted": submitted,
        "quote_work": quote_work,
        "leads": leads,
        "today_moves": today_moves[:6],
        "summary": {
            "active": len(opportunities),
            "due_soon": len(due_soon),
            "followups_due": len(followups_due),
            "submitted": len(submitted),
            "open_profit": _money_fmt(open_profit),
            "expected_pipeline": _money_fmt(expected_pipeline),
        },
    }
