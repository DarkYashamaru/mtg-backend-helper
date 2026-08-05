from sqlalchemy import text
from database.base import Base
from database.session import engine, get_engine
from tools.card_lookup import (
    normalize_card_name,
    normalize_collector_number,
    normalize_set_code,
)

# import all models
from models.card import *
from models.collection import *
from models.users import *


def create_database():
    run_compatibility_migrations()

    # 1. Create the structural tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # 2. Optimize the file structure via Vacuum
    vacuum_database()


def vacuum_database():
    """Defragments and shrinks the SQLite file on disk safely from Python."""
    dynamic_engine = get_engine()
    
    with dynamic_engine.connect() as conn:
        # We must explicitly bypass the transaction wrapper for VACUUM to work
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(text("VACUUM;"))


def run_compatibility_migrations():
    dynamic_engine = get_engine()

    with dynamic_engine.begin() as conn:
        collection_columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(collections)")).fetchall()
        }

        if collection_columns and "user_id" not in collection_columns:
            collections_count = conn.execute(text("SELECT COUNT(*) FROM collections")).scalar_one()
            collection_items_count = conn.execute(text("SELECT COUNT(*) FROM collection_items")).scalar_one()

            # Old schema detected. When no collection data exists yet, rebuild the tables
            # so the SQLAlchemy metadata can recreate them with the current structure.
            if collections_count == 0 and collection_items_count == 0:
                conn.execute(text("DROP TABLE IF EXISTS collection_items"))
                conn.execute(text("DROP TABLE IF EXISTS collections"))
            else:
                # Preserve legacy data if it exists, even though the rebuilt schema will
                # still need a manual follow-up migration for proper FK/index creation.
                conn.execute(text("ALTER TABLE collections ADD COLUMN user_id INTEGER"))

        card_columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(cards)")).fetchall()
        }

        if card_columns:
            if "name_normalized" not in card_columns:
                conn.execute(text("ALTER TABLE cards ADD COLUMN name_normalized VARCHAR"))
            if "set_code_normalized" not in card_columns:
                conn.execute(text("ALTER TABLE cards ADD COLUMN set_code_normalized VARCHAR"))
            if "collector_number_normalized" not in card_columns:
                conn.execute(text("ALTER TABLE cards ADD COLUMN collector_number_normalized VARCHAR"))

            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_cards_lookup_exact "
                    "ON cards (name_normalized, set_code_normalized, collector_number_normalized)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_cards_lookup_fallback "
                    "ON cards (name_normalized, set_code_normalized)"
                )
            )

            rows_to_backfill = conn.execute(
                text(
                    "SELECT id, name, set_code, collector_number "
                    "FROM cards "
                    "WHERE name_normalized IS NULL "
                    "OR set_code_normalized IS NULL "
                    "OR collector_number_normalized IS NULL"
                )
            ).fetchall()

            if rows_to_backfill:
                conn.execute(
                    text(
                        "UPDATE cards "
                        "SET name_normalized = :name_normalized, "
                        "set_code_normalized = :set_code_normalized, "
                        "collector_number_normalized = :collector_number_normalized "
                        "WHERE id = :id"
                    ),
                    [
                        {
                            "id": row[0],
                            "name_normalized": normalize_card_name(row[1] or ""),
                            "set_code_normalized": normalize_set_code(row[2] or ""),
                            "collector_number_normalized": normalize_collector_number(row[3] or ""),
                        }
                        for row in rows_to_backfill
                    ],
                )

    dynamic_engine.dispose()
