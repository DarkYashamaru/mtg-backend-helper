from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from sqlalchemy import select
import ijson  # Added for memory-efficient JSON streaming

from database.session import session_scope 
from models.card import CardPrint, CardPrintFace, CardPrintImage, ImageType
from tools.logger import logger
from downloaders.download_all_cards import ALL_CARDS_PATH

# Target destination for the flattened relationship data
RELATIONSHIPS_PATH = Path("data/relationships/card_relationships.jsonl")


def map_json_to_card_model(data: dict[str, Any]) -> CardPrint:
    """Maps raw Scryfall JSON data straight to the CardPrint SQLAlchemy model."""

    oracle_id = data.get("oracle_id")
    if not oracle_id and "card_faces" in data:
        oracle_id = data["card_faces"][0].get("oracle_id")

    card = CardPrint(
        id=data["id"],
        oracle_id=oracle_id,
        name=data["name"],
        lang=data["lang"],
        released_at=data["released_at"],
        scryfall_uri=data["scryfall_uri"],
        layout=data["layout"],
        rarity=data.get("rarity", "common"),
        set_code=data.get("set", ""),
        set_name=data.get("set_name", ""),
        collector_number=data.get("collector_number", ""),
        price_usd=data.get("prices", {}).get("usd"),
        price_usd_foil=data.get("prices", {}).get("usd_foil"),
        price_eur=data.get("prices", {}).get("eur")
    )
    
    # Extract top-level images
    if "image_uris" in data:
        for img_type, uri in data["image_uris"].items():
            try:
                card.images.append(CardPrintImage(image_type=ImageType(img_type), uri=uri))
            except ValueError:
                continue
            
    # Extract structural sub-faces (Adventure, Flip, Double-Sided)
    if "card_faces" in data:
        for face_data in data["card_faces"]:
            face = CardPrintFace(
                name=face_data["name"],
                flavor_text=face_data.get("flavor_text"),
                artist=face_data.get("artist")
            )
            
            # Sub-face specific images (Transform cards)
            if "image_uris" in face_data:
                for img_type, uri in face_data["image_uris"].items():
                    try:
                        face.images.append(CardPrintImage(image_type=ImageType(img_type), uri=uri))
                    except ValueError:
                        continue
                        
            card.faces.append(face)
        
    return card


def stream_card_relationships(data: dict[str, Any], jsonl_file) -> None:
    """Extracts all_parts from a card and appends them to the open jsonl file descriptor."""
    card_id = data.get("id")
    all_parts = data.get("all_parts", [])

    if not card_id or not all_parts:
        return

    for part in all_parts:
        related_id = part.get("id")
        
        # Avoid creating self-referencing relationships
        if card_id == related_id:
            continue

        flattened_relation = {
            "card_id": card_id,
            "related_id": related_id,
            "component": part.get("component")
        }
        
        # Write directly to disk as a single line JSON block
        jsonl_file.write(json.dumps(flattened_relation) + "\n")


def import_card_prints(source_path: Path = ALL_CARDS_PATH) -> int:
    """
    Streams a Scryfall bulk JSON file and inserts eligible new card printings
    into the database. Lazily opens the relationship JSONL file ONLY when 
    there are actual new printings to process, preventing accidental 0-byte truncation.
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Scryfall bulk cards JSON not found at {source_path}.")

    # Ensure the target directory for relationships exists
    RELATIONSHIPS_PATH.parent.mkdir(parents=True, exist_ok=True)

    if RELATIONSHIPS_PATH.exists():
        logger.info(f"Removing stale relationship tracking file: {RELATIONSHIPS_PATH.name}")
        RELATIONSHIPS_PATH.unlink()

    logger.info("Loading existing print IDs from database...")
    with session_scope() as session:
        existing_ids = set(session.scalars(select(CardPrint.id)).all())

    imported_count = 0
    BATCH_SIZE = 1000  # Safe size for frequent database syncing
    jsonl_file = None  # Pointer starts as None to protect existing disk files

    logger.info("Beginning low-RAM card print streaming execution...")
    
    try:
        with session_scope() as session:
            with source_path.open(encoding="utf-8") as file:
                payload_stream = ijson.items(file, "item")
                
                for item in payload_stream:
                    print_id = item.get("id")
                    if not print_id or print_id in existing_ids:
                        continue

                    layout = item.get("layout") or ""

                    # 1. Format Filter
                    legalities = item.get("legalities") or {}
                    is_commander = legalities.get("commander") == "legal"
                    is_standard = legalities.get("standard") == "legal"
                    
                    if layout != "token" and not (is_commander or is_standard):
                        continue

                    # 2. Layout Filter
                    if layout in {"", "art_series", "scheme", "memorabilia"}:
                        continue

                    # 3. Lazy File Initialization
                    # This block only triggers if a card successfully clears all filters above
                    if jsonl_file is None:
                        logger.info(f"New data detected. Opening {RELATIONSHIPS_PATH.name} for writing...")
                        jsonl_file = RELATIONSHIPS_PATH.open("w", encoding="utf-8")

                    # 4. Model Translation & Generation
                    try:
                        card_print = map_json_to_card_model(item)
                        session.add(card_print)
                        
                        # Safe to stream now that the file handle is guaranteed open
                        stream_card_relationships(item, jsonl_file)
                        
                        imported_count += 1
                        
                        if imported_count % BATCH_SIZE == 0:
                            session.commit()
                            session.expunge_all() 
                            logger.info(f"Saved batch: {imported_count} total cards imported...")
                            
                    except Exception as e:
                        logger.error(f"Failed to parse print execution {print_id}: {e}")
                        continue

            # Final pass commit to secure remaining odd-numbered rows
            if imported_count % BATCH_SIZE != 0:
                session.commit()
                session.expunge_all()

    finally:
        # The finally block guarantees the file is closed even if the script crashes mid-stream
        if jsonl_file is not None:
            logger.info("Closing relationship batch file stream...")
            jsonl_file.close()

    logger.info(f"Finished! Successfully imported {imported_count} card printings.")
    return imported_count