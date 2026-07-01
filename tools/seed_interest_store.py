from __future__ import annotations

import csv
import io
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

DB_PATH = Path(os.getenv("SEED_INTEREST_DB_PATH", "data/seed_interest.sqlite3"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clean(value: object, limit: int = 2000) -> str:
    return str(value or "").strip()[:limit]


def _checked(value: object) -> int:
    return 1 if str(value or "").lower() in {"on", "true", "1", "yes", "y"} else 0


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS drop_list (
            id TEXT PRIMARY KEY,
            name TEXT DEFAULT '',
            email TEXT NOT NULL,
            phone TEXT DEFAULT '',
            state TEXT DEFAULT '',
            interest TEXT DEFAULT '',
            age_confirmed INTEGER DEFAULT 0,
            legal_confirmed INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS genetics_inquiries (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT DEFAULT '',
            state TEXT DEFAULT '',
            catalog_interest TEXT DEFAULT '',
            buyer_type TEXT DEFAULT '',
            message TEXT DEFAULT '',
            age_confirmed INTEGER DEFAULT 0,
            legal_confirmed INTEGER DEFAULT 0,
            no_payment_sent INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    return conn


def init_seed_interest_db() -> None:
    with _conn():
        pass


def catalog() -> List[Dict[str, str]]:
    return [
        {
            "name": "Tropicana Cookie Line",
            "type": "Small-batch genetics interest",
            "profile": "Citrus-cookie terp direction, purple-expression hunt, brand drop planning.",
            "status": "Drop list open",
        },
        {
            "name": "Midwest Utility Pack",
            "type": "Collector genetics interest",
            "profile": "Practical, resilient, easy-to-document genetics concept for lawful jurisdictions only.",
            "status": "Research list",
        },
        {
            "name": "Private Breeder / White Label Inquiry",
            "type": "B2B inquiry",
            "profile": "For lawful sourcing conversations, documentation review, and future batch planning.",
            "status": "Manual review",
        },
    ]


def save_drop_list(data: Dict[str, object]) -> str:
    entry_id = str(uuid.uuid4())
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO drop_list (id, name, email, phone, state, interest, age_confirmed, legal_confirmed, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_id,
                _clean(data.get("name"), 120),
                _clean(data.get("email"), 220),
                _clean(data.get("phone"), 80),
                _clean(data.get("state"), 40),
                _clean(data.get("interest"), 500),
                _checked(data.get("age_confirmed")),
                _checked(data.get("legal_confirmed")),
                _now(),
            ),
        )
    return entry_id


def save_inquiry(data: Dict[str, object]) -> str:
    inquiry_id = str(uuid.uuid4())
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO genetics_inquiries (
                id, name, email, phone, state, catalog_interest, buyer_type, message,
                age_confirmed, legal_confirmed, no_payment_sent, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                inquiry_id,
                _clean(data.get("name"), 120),
                _clean(data.get("email"), 220),
                _clean(data.get("phone"), 80),
                _clean(data.get("state"), 40),
                _clean(data.get("catalog_interest"), 120),
                _clean(data.get("buyer_type"), 120),
                _clean(data.get("message"), 2000),
                _checked(data.get("age_confirmed")),
                _checked(data.get("legal_confirmed")),
                _checked(data.get("no_payment_sent")),
                _now(),
            ),
        )
    return inquiry_id


def list_drop_list(limit: int = 300) -> List[Dict[str, object]]:
    init_seed_interest_db()
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM drop_list ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def list_inquiries(limit: int = 300) -> List[Dict[str, object]]:
    init_seed_interest_db()
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM genetics_inquiries ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def lead_counts() -> Dict[str, int]:
    init_seed_interest_db()
    with _conn() as conn:
        drop_count = conn.execute("SELECT COUNT(*) FROM drop_list").fetchone()[0]
        inquiry_count = conn.execute("SELECT COUNT(*) FROM genetics_inquiries").fetchone()[0]
    return {"drop_list": int(drop_count), "inquiries": int(inquiry_count), "total": int(drop_count) + int(inquiry_count)}


def leads_csv() -> str:
    drop_list = list_drop_list(limit=5000)
    inquiries = list_inquiries(limit=5000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["type", "created_at", "name", "email", "phone", "state", "interest", "buyer_type", "message", "age_confirmed", "legal_confirmed", "no_payment_sent"])
    for row in drop_list:
        writer.writerow(["drop_list", row.get("created_at", ""), row.get("name", ""), row.get("email", ""), row.get("phone", ""), row.get("state", ""), row.get("interest", ""), "", "", row.get("age_confirmed", 0), row.get("legal_confirmed", 0), ""])
    for row in inquiries:
        writer.writerow(["genetics_inquiry", row.get("created_at", ""), row.get("name", ""), row.get("email", ""), row.get("phone", ""), row.get("state", ""), row.get("catalog_interest", ""), row.get("buyer_type", ""), row.get("message", ""), row.get("age_confirmed", 0), row.get("legal_confirmed", 0), row.get("no_payment_sent", 0)])
    return output.getvalue()
