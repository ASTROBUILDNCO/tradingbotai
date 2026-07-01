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
            name TEXT DEFAULT '', email TEXT NOT NULL, phone TEXT DEFAULT '', state TEXT DEFAULT '',
            interest TEXT DEFAULT '', age_confirmed INTEGER DEFAULT 0, legal_confirmed INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS genetics_inquiries (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT DEFAULT '', state TEXT DEFAULT '',
            catalog_interest TEXT DEFAULT '', buyer_type TEXT DEFAULT '', message TEXT DEFAULT '',
            age_confirmed INTEGER DEFAULT 0, legal_confirmed INTEGER DEFAULT 0, no_payment_sent INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reservation_requests (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT DEFAULT '', state TEXT DEFAULT '',
            product TEXT DEFAULT '', pack_size TEXT DEFAULT '', quantity TEXT DEFAULT '',
            payment_preference TEXT DEFAULT '', message TEXT DEFAULT '', status TEXT DEFAULT 'new_request',
            age_confirmed INTEGER DEFAULT 0, legal_confirmed INTEGER DEFAULT 0, no_payment_sent INTEGER DEFAULT 0,
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
        {"slug":"tropicana-cookies-auto","name":"Tropicana Cookies Auto","type":"Auto / limited current stock","inventory":"2 packs available now","badge":"2 live","status":"Limited","visual":"trop","profile":"Flagship citrus-cookie direction: loud orange peel, cookie funk, purple lean, and premium bag appeal.","future":"Core inspiration lane for Astro Cookies Auto work."},
        {"slug":"gorilla-cookies-auto","name":"Gorilla Cookies Auto","type":"Auto / current stock","inventory":"10 packs available now","badge":"10 live","status":"Available","visual":"gorilla","profile":"Heavy cookie-gas lane with big name recognition and broad first-menu appeal.","future":"Use as the practical high-demand auto while the house line develops."},
        {"slug":"orange-sherbet-auto","name":"Orange Sherbet Auto","type":"Auto / current stock","inventory":"7 packs available now","badge":"7 live","status":"Available","visual":"sherb","profile":"Sweet orange cream branding, softer dessert profile, and a clean citrus companion to Tropicana Cookies.","future":"Strong content strain for citrus comparison diaries."},
        {"slug":"astro-cookies-auto-s3","name":"Astro Cookies Auto S3","type":"Future in-house line","inventory":"Coming after selection work","badge":"S3 target","status":"Future Drop","visual":"astro","profile":"The first house-signature concept: cookie/citrus auto genetics documented through transparent selection notes.","future":"Make this the brand signature after enough stability, documentation, and proof."},
        {"slug":"og-kush-pheno-hunt","name":"OG Kush Pheno Hunt","type":"Future photo line","inventory":"Coming after pheno hunt","badge":"hunt","status":"In Development","visual":"og","profile":"Classic gas, pine, fuel, and old-school structure. Built only after you select a keeper pheno worth attaching the brand to.","future":"Future premium photo line once a winner is hunted and documented."},
    ]


def grow_diary() -> List[Dict[str, str]]:
    return [
        {"title":"Current Inventory Drop","body":"Gorilla Cookies Auto 10, Orange Sherbet Auto 7, Tropicana Cookies Auto 2. First menu should stay honest and limited."},
        {"title":"Astro Cookies Auto S3 Goal","body":"Document the parent selection, keeper traits, germ tests, structure, terp direction, and why the line deserves the Astro name."},
        {"title":"OG Kush Keeper Hunt","body":"Do not rush the OG line. Build demand with photos, notes, and a real keeper story before release."},
    ]


def save_drop_list(data: Dict[str, object]) -> str:
    entry_id = str(uuid.uuid4())
    with _conn() as conn:
        conn.execute("INSERT INTO drop_list (id,name,email,phone,state,interest,age_confirmed,legal_confirmed,created_at) VALUES (?,?,?,?,?,?,?,?,?)", (entry_id,_clean(data.get("name"),120),_clean(data.get("email"),220),_clean(data.get("phone"),80),_clean(data.get("state"),40),_clean(data.get("interest"),500),_checked(data.get("age_confirmed")),_checked(data.get("legal_confirmed")),_now()))
    return entry_id


def save_inquiry(data: Dict[str, object]) -> str:
    inquiry_id = str(uuid.uuid4())
    with _conn() as conn:
        conn.execute("INSERT INTO genetics_inquiries (id,name,email,phone,state,catalog_interest,buyer_type,message,age_confirmed,legal_confirmed,no_payment_sent,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (inquiry_id,_clean(data.get("name"),120),_clean(data.get("email"),220),_clean(data.get("phone"),80),_clean(data.get("state"),40),_clean(data.get("catalog_interest"),120),_clean(data.get("buyer_type"),120),_clean(data.get("message"),2000),_checked(data.get("age_confirmed")),_checked(data.get("legal_confirmed")),_checked(data.get("no_payment_sent")),_now()))
    return inquiry_id


def save_reservation(data: Dict[str, object]) -> str:
    request_id = str(uuid.uuid4())
    with _conn() as conn:
        conn.execute("INSERT INTO reservation_requests (id,name,email,phone,state,product,pack_size,quantity,payment_preference,message,status,age_confirmed,legal_confirmed,no_payment_sent,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (request_id,_clean(data.get("name"),120),_clean(data.get("email"),220),_clean(data.get("phone"),80),_clean(data.get("state"),40),_clean(data.get("product"),160),_clean(data.get("pack_size"),80),_clean(data.get("quantity"),40),_clean(data.get("payment_preference"),120),_clean(data.get("message"),2000),"new_request",_checked(data.get("age_confirmed")),_checked(data.get("legal_confirmed")),_checked(data.get("no_payment_sent")),_now()))
    return request_id


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


def list_reservations(limit: int = 300) -> List[Dict[str, object]]:
    init_seed_interest_db()
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM reservation_requests ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def lead_counts() -> Dict[str, int]:
    init_seed_interest_db()
    with _conn() as conn:
        drop_count = conn.execute("SELECT COUNT(*) FROM drop_list").fetchone()[0]
        inquiry_count = conn.execute("SELECT COUNT(*) FROM genetics_inquiries").fetchone()[0]
        reservation_count = conn.execute("SELECT COUNT(*) FROM reservation_requests").fetchone()[0]
    total = int(drop_count) + int(inquiry_count) + int(reservation_count)
    return {"drop_list": int(drop_count), "inquiries": int(inquiry_count), "reservations": int(reservation_count), "total": total}


def leads_csv() -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["type","created_at","status","name","email","phone","state","interest_or_product","pack_size","quantity","buyer_or_payment","message","age_confirmed","legal_confirmed","no_payment_sent"])
    for row in list_drop_list(limit=5000):
        writer.writerow(["drop_list",row.get("created_at",""),"",row.get("name",""),row.get("email",""),row.get("phone",""),row.get("state",""),row.get("interest",""),"","","","",row.get("age_confirmed",0),row.get("legal_confirmed",0),""])
    for row in list_inquiries(limit=5000):
        writer.writerow(["inquiry",row.get("created_at",""),"",row.get("name",""),row.get("email",""),row.get("phone",""),row.get("state",""),row.get("catalog_interest",""),"","",row.get("buyer_type",""),row.get("message",""),row.get("age_confirmed",0),row.get("legal_confirmed",0),row.get("no_payment_sent",0)])
    for row in list_reservations(limit=5000):
        writer.writerow(["reservation",row.get("created_at",""),row.get("status",""),row.get("name",""),row.get("email",""),row.get("phone",""),row.get("state",""),row.get("product",""),row.get("pack_size",""),row.get("quantity",""),row.get("payment_preference",""),row.get("message",""),row.get("age_confirmed",0),row.get("legal_confirmed",0),row.get("no_payment_sent",0)])
    return output.getvalue()
