"""Shared SQLite access for chat history persistence.

`chat_messages` already existed in the seed database with exactly the shape this
feature needs (id, user_id, role, content, products_json, created_at) — so rather
than invent a second table, this creates that same table only if it's missing
(CREATE TABLE IF NOT EXISTS), which is also what makes a fresh clone without
data/ work: the table gets created automatically the first time the app runs.
Existing tables (`users`, `catalogue`, `inventory`) are never touched.
"""

import json
import sqlite3
from pathlib import Path

from .models import ChatHistoryEntry, ProductCard

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DB_PATH = PROJECT_ROOT / "data" / "campus_customs.db"


def get_connection() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def ensure_schema() -> None:
    con = get_connection()
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                products_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        con.commit()
    finally:
        con.close()


def save_chat_message(user_id: int, role: str, content: str, products: list[ProductCard] | None = None) -> None:
    products_json = json.dumps([p.model_dump() for p in products]) if products else None
    con = get_connection()
    try:
        con.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, ?, ?, ?)",
            (user_id, role, content, products_json),
        )
        con.commit()
    finally:
        con.close()


def clear_chat_history(user_id: int) -> None:
    con = get_connection()
    try:
        con.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
        con.commit()
    finally:
        con.close()


def load_chat_history(user_id: int, limit: int | None = None) -> list[ChatHistoryEntry]:
    con = get_connection()
    try:
        rows = con.execute(
            "SELECT role, content, products_json, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY id",
            (user_id,),
        ).fetchall()
    finally:
        con.close()

    if limit is not None:
        rows = rows[-limit:]

    entries = []
    for row in rows:
        products = [ProductCard(**p) for p in json.loads(row["products_json"])] if row["products_json"] else []
        entries.append(
            ChatHistoryEntry(
                role=row["role"], content=row["content"], products=products, created_at=row["created_at"]
            )
        )
    return entries
