from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Dict, Optional

try:
    from cryptography.fernet import Fernet
except Exception:
    Fernet = None

DB_PATH = Path(os.getenv("CONFIG_DB_PATH", "data/astro_config.sqlite3"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SECRET_KEYS = [
    "OPENAI_API_KEY",
    "EMAIL_PROVIDER",
    "IMAP_HOST",
    "IMAP_PORT",
    "IMAP_USER",
    "IMAP_PASSWORD",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "META_PAGE_ID",
    "META_PAGE_ACCESS_TOKEN",
    "APPROVAL_REQUIRED",
    "TIMEZONE",
]


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    return conn


def _fernet():
    key = os.getenv("CONFIG_ENCRYPTION_KEY")
    if key and Fernet is not None:
        return Fernet(key.encode())
    return None


def encrypt_value(value: str) -> str:
    f = _fernet()
    if f:
        return "fernet:" + f.encrypt(value.encode()).decode()
    return "plain:" + value


def decrypt_value(value: str) -> str:
    if value.startswith("fernet:"):
        f = _fernet()
        if not f:
            return ""
        return f.decrypt(value[len("fernet:"):].encode()).decode()
    if value.startswith("plain:"):
        return value[len("plain:"):]
    return value


def save_setting(key: str, value: str) -> None:
    if key not in SECRET_KEYS:
        raise ValueError(f"Unsupported setting: {key}")
    with _conn() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, encrypt_value(value)))


def load_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    env_val = os.getenv(key)
    if env_val not in (None, ""):
        return env_val
    with _conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if not row:
        return default
    return decrypt_value(row[0])


def load_all_masked() -> Dict[str, str]:
    out: Dict[str, str] = {}
    with _conn() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    stored = {k: decrypt_value(v) for k, v in rows}
    for key in SECRET_KEYS:
        val = os.getenv(key) or stored.get(key, "")
        if not val:
            out[key] = ""
        elif "PASSWORD" in key or "TOKEN" in key or "KEY" in key:
            out[key] = val[:4] + "..." + val[-4:] if len(val) > 8 else "saved"
        else:
            out[key] = val
    return out
