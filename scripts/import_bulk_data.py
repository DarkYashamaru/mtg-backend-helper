from pathlib import Path
import gzip
import json
import sqlite3
import re
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "card_cache.sqlite3"
JSON_PATH = BASE_DIR / "cards.jsonl.gz"

DB_PATH = BASE_DIR / "card_cache.sqlite3"
JSON_PATH = BASE_DIR / "cards.jsonl.gz"


def normalize_name(name):
    return re.sub(r"\s+", " ", name).strip().casefold()


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


def main():
    print("Opening database...")

    conn = sqlite3.connect(DB_PATH)

    conn.execute("PRAGMA journal_mode=WAL;")

    init_db(conn)

    print("Streaming JSONL gzip archive...")

    now = datetime.now(timezone.utc).isoformat()

    inserted = 0
    skipped = 0

    for line in gzip.open(JSON_PATH, "rt", encoding="utf-8"):
        line = line.strip()
        if not line:
            skipped += 1
            continue

        try:
            card = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue

        name = card.get("name")

        if not name:
            skipped += 1
            continue

        lookup_name = normalize_name(name)

        conn.execute(
            """
            INSERT OR REPLACE INTO cards
            (
                lookup_name,
                card_name,
                found,
                card_json,
                fetched_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                lookup_name,
                name,
                1,
                json.dumps(card),
                now
            )
        )

        inserted += 1

        if inserted % 1000 == 0:
            print(f"Imported {inserted} cards...")

    print("Committing database...")

    conn.commit()

    conn.close()

    print()
    print(f"Done.")
    print(f"Inserted: {inserted}")
    print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()
