import json
from pathlib import Path
from sqlalchemy import select, insert
from database.session import session_scope
from models.card import CardPrint, CardRelationship
from tools.logger import logger
from importers.card_importer import RELATIONSHIPS_PATH


def import_relationships(source_path: Path = RELATIONSHIPS_PATH, batch_size: int = 5000) -> int:
    """
    Reads the intermediary JSONL relationships file line-by-line and bulk-inserts
    connections into the database if both matching card prints exist.
    """
    if not source_path.exists():
        logger.error(f"Intermediary relationship file not found at {source_path}. Run card importer first.")
        return 0

    logger.info("Caching existing card IDs to protect Foreign Key integrity...")
    with session_scope() as session:
        # Load all valid IDs into a memory set (~40-60MB RAM total, perfectly acceptable)
        valid_card_ids = set(session.scalars(select(CardPrint.id)).all())

    logger.info(f"Loaded {len(valid_card_ids)} valid destination card references. Commencing streaming...")

    inserted_relations_count = 0
    skipped_count = 0
    batch_buffer = []

    with session_scope() as session:
        with source_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    relation_data = json.loads(line)
                    card_id = relation_data.get("card_id")
                    related_id = relation_data.get("related_id")

                    # Verify both records exist locally to prevent constraint execution faults
                    if card_id not in valid_card_ids or related_id not in valid_card_ids:
                        skipped_count += 1
                        continue

                    batch_buffer.append({
                        "card_id": card_id,
                        "related_id": related_id,
                        "component": relation_data.get("component", "unknown")
                    })

                    # Trigger a rapid high-performance bulk insert once chunk threshold hits
                    if len(batch_buffer) >= batch_size:
                        session.execute(insert(CardRelationship), batch_buffer)
                        session.commit()
                        inserted_relations_count += len(batch_buffer)
                        logger.info(f"Inserted {inserted_relations_count} relationship connections...")
                        batch_buffer.clear()

                except Exception as e:
                    logger.error(f"Error parsing relationship tracking row mapping sequence: {e}")
                    continue

            # Safely flush leftover database rows out of buffer array
            if batch_buffer:
                session.execute(insert(CardRelationship), batch_buffer)
                session.commit()
                inserted_relations_count += len(batch_buffer)

    logger.info(
        f"Success! Finished importing relationships.\n"
        f"-> Total Relations Recorded: {inserted_relations_count}\n"
        f"-> Total Dead Relations Filtered Out: {skipped_count}"
    )
    return inserted_relations_count


if __name__ == "__main__":
    import_relationships()