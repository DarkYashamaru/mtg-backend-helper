import sqlite3
import json
import re
from datetime import datetime, timezone

DB_PATH = "card_cache.sqlite3"


def normalize_name(name):
    return re.sub(r"\s+", " ", name).strip().casefold()


def get_connection():
    conn = sqlite3.connect(DB_PATH)

    conn.execute("PRAGMA journal_mode=WAL;")

    return conn


def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            lookup_name TEXT PRIMARY KEY,
            card_name   TEXT NOT NULL,
            found       INTEGER NOT NULL,
            card_json   TEXT,
            fetched_at  TEXT NOT NULL
        )
    """)

    conn.commit()


def get_cached_card(conn, name):
    lookup_name = normalize_name(name)

    cur = conn.execute(
        "SELECT found, card_json FROM cards WHERE lookup_name = ?",
        (lookup_name,)
    )

    row = cur.fetchone()

    if row is None:
        return None, False

    found, card_json_text = row

    if found:
        return json.loads(card_json_text), True

    return None, True


def save_card(conn, name, card_json):
    lookup_name = normalize_name(name)

    now = datetime.now(timezone.utc).isoformat()

    if card_json is None:
        return

    else:
        conn.execute(
            """
            INSERT OR REPLACE INTO cards
            (lookup_name, card_name, found, card_json, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                lookup_name,
                name,
                1,
                json.dumps(card_json),
                now
            )
        )

    conn.commit()
