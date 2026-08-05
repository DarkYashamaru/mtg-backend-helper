from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models.card import CardPrint, CardPrintImage, ImageType
from models.collection import Collection, CollectionItem, DeckType
from models.users import User
from tools.card_lookup import (
    normalize_card_name,
    normalize_collector_number,
    normalize_set_code,
)


LINE_PATTERN = re.compile(
    r"^(?P<amount>\d+)x\s+"
    r"(?P<name>.+?)\s+"
    r"\((?P<set_code>[^)]+)\)\s+"
    r"(?P<collector_number>\S+)"
    r"(?:\s+\*F\*)?"
    r"(?:\s+\[(?P<labels>[^\]]*)\])?\s*$"
)

ZONE_BY_HEADER = {
    "commander": "commander",
    "mainboard": "mainboard",
    "sideboard": "sideboard",
    "maybeboard": "maybeboard",
}


class CollectionError(ValueError):
    """Base error for collection operations."""


class CollectionParseError(CollectionError):
    """Raised when a decklist line cannot be parsed."""


class CollectionCardLookupError(CollectionError):
    """Raised when an imported line cannot be resolved to a card."""


class CollectionNotFoundError(CollectionError):
    """Raised when a collection does not exist for the current user."""


@dataclass(frozen=True)
class ParsedCollectionLine:
    amount: int
    card_name: str
    set_code: str
    collector_number: str
    zone: str
    raw_line: str


def _normalize_collector_number(value: str) -> str:
    return normalize_collector_number(value)


def _parse_collection_lines(deck_text: str) -> list[ParsedCollectionLine]:
    current_zone = "mainboard"
    parsed_lines: list[ParsedCollectionLine] = []

    for raw_line in deck_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        header_key = line.casefold()
        if header_key in ZONE_BY_HEADER:
            current_zone = ZONE_BY_HEADER[header_key]
            continue

        match = LINE_PATTERN.fullmatch(line)
        if not match:
            raise CollectionParseError(f"Could not parse deck line: {line}")

        parsed_lines.append(
            ParsedCollectionLine(
                amount=int(match.group("amount")),
                card_name=match.group("name").strip(),
                set_code=normalize_set_code(match.group("set_code")),
                collector_number=match.group("collector_number").strip(),
                zone=current_zone,
                raw_line=line,
            )
        )

    if not parsed_lines:
        raise CollectionParseError("The submitted deck list did not contain any card lines.")

    return parsed_lines


def _pick_best_card(cards: Iterable[CardPrint]) -> CardPrint | None:
    ordered = sorted(cards, key=lambda card: (card.lang != "en", card.released_at, card.id))
    return ordered[0] if ordered else None


def _resolve_card_prints(db: Session, parsed_lines: list[ParsedCollectionLine]) -> dict[int, CardPrint]:
    unique_set_codes = {line.set_code for line in parsed_lines}
    unique_names = {normalize_card_name(line.card_name) for line in parsed_lines}

    statement = select(CardPrint).where(
        CardPrint.set_code_normalized.in_(unique_set_codes),
        CardPrint.name_normalized.in_(unique_names),
    )
    candidates = list(db.execute(statement).scalars())

    exact_lookup: dict[tuple[str, str, str], CardPrint] = {}
    fallback_lookup: dict[tuple[str, str], list[CardPrint]] = {}

    for card in candidates:
        name_normalized = card.name_normalized or normalize_card_name(card.name)
        set_code_normalized = card.set_code_normalized or normalize_set_code(card.set_code)
        collector_number_normalized = (
            card.collector_number_normalized
            or normalize_collector_number(card.collector_number)
        )

        exact_key = (name_normalized, set_code_normalized, collector_number_normalized)
        current_exact = exact_lookup.get(exact_key)
        if current_exact is None:
            exact_lookup[exact_key] = card
        else:
            exact_lookup[exact_key] = _pick_best_card([current_exact, card]) or current_exact

        fallback_key = (name_normalized, set_code_normalized)
        fallback_lookup.setdefault(fallback_key, []).append(card)

    resolved_cards: dict[int, CardPrint] = {}

    for index, line in enumerate(parsed_lines):
        name_normalized = normalize_card_name(line.card_name)
        collector_normalized = normalize_collector_number(line.collector_number)
        set_code_normalized = line.set_code

        exact_key = (name_normalized, set_code_normalized, collector_normalized)
        selected = exact_lookup.get(exact_key)

        if selected is None:
            fallback_key = (name_normalized, set_code_normalized)
            selected = _pick_best_card(fallback_lookup.get(fallback_key, []))

        if selected is None:
            raise CollectionCardLookupError(
                f"Could not resolve card '{line.card_name}' ({line.set_code}) {line.collector_number}."
            )

        resolved_cards[index] = selected

    return resolved_cards


def _infer_collection_name(name: str | None, parsed_lines: list[ParsedCollectionLine]) -> str:
    if name and name.strip():
        return name.strip()

    commander_line = next((line for line in parsed_lines if line.zone == "commander"), None)
    if commander_line is not None:
        return f"{commander_line.card_name} Bulk Deck"

    first_line = parsed_lines[0]
    return f"{first_line.card_name} Collection"


def _infer_deck_type(parsed_lines: list[ParsedCollectionLine]) -> DeckType:
    if any(line.zone == "commander" for line in parsed_lines):
        return DeckType.COMMANDER
    return DeckType.BINDER


def _coerce_deck_type(value: DeckType | str | None, parsed_lines: list[ParsedCollectionLine]) -> DeckType:
    if isinstance(value, DeckType):
        return value

    if isinstance(value, str):
        normalized = value.strip().casefold()
        for deck_type in DeckType:
            if deck_type.value.casefold() == normalized:
                return deck_type

    return _infer_deck_type(parsed_lines)


def _replace_collection_items(db: Session, collection: Collection, parsed_lines: list[ParsedCollectionLine]) -> None:
    collection.items.clear()
    commander_card_id: str | None = None
    merged_items: dict[tuple[str, str], int] = {}
    resolved_cards = _resolve_card_prints(db, parsed_lines)

    for index, line in enumerate(parsed_lines):
        card = resolved_cards[index]
        key = (card.id, line.zone)
        merged_items[key] = merged_items.get(key, 0) + line.amount
        if line.zone == "commander" and commander_card_id is None:
            commander_card_id = card.id

    for (card_id, zone), amount in merged_items.items():
        collection.items.append(
            CollectionItem(
                card_id=card_id,
                amount=amount,
                zone=zone,
            )
        )

    collection.commander_card_id = commander_card_id


def _collection_query_for_user(user_id: int):
    return (
        select(Collection)
        .where(Collection.user_id == user_id)
        .options(
            selectinload(Collection.items).selectinload(CollectionItem.card).selectinload(CardPrint.images),
            selectinload(Collection.commander_card).selectinload(CardPrint.images),
        )
        .order_by(Collection.id.desc())
    )


def serialize_collection_item(item: CollectionItem) -> dict:
    card = item.card
    return {
        "id": item.id,
        "card_id": item.card_id,
        "oracle_id": card.oracle_id if card else None,
        "name": card.name if card else None,
        "set_code": card.set_code if card else None,
        "collector_number": card.collector_number if card else None,
        "lang": card.lang if card else None,
        "image_uri": _commander_image_uri(card),
        "amount": item.amount,
        "zone": item.zone,
    }


def _commander_image_uri(card: CardPrint | None) -> str | None:
    if card is None:
        return None

    preferred_order = (
        ImageType.NORMAL,
        ImageType.SMALL,
        ImageType.LARGE,
        ImageType.PNG,
        ImageType.ART_CROP,
        ImageType.BORDER_CROP,
    )

    images_by_type = {
        image.image_type: image.uri
        for image in card.images
    }

    for image_type in preferred_order:
        uri = images_by_type.get(image_type)
        if uri:
            return uri

    return None


def serialize_collection(collection: Collection, *, include_items: bool = True) -> dict:
    items = sorted(collection.items, key=lambda item: (item.zone, item.card.name if item.card else "", item.card_id))
    return {
        "id": collection.id,
        "user_id": collection.user_id,
        "name": collection.name,
        "deck_type": collection.deck_type.value if isinstance(collection.deck_type, DeckType) else str(collection.deck_type),
        "commander_card_id": collection.commander_card_id,
        "commander_oracle_id": collection.commander_card.oracle_id if collection.commander_card else None,
        "commander_name": collection.commander_card.name if collection.commander_card else None,
        "commander_image_uri": _commander_image_uri(collection.commander_card),
        "item_count": sum(item.amount for item in items),
        "items": [serialize_collection_item(item) for item in items] if include_items else [],
    }


def create_collection_from_deck_text(
    db: Session,
    user: User,
    name: str | None,
    deck_text: str,
    deck_type: DeckType | str | None = None,
) -> Collection:
    parsed_lines = _parse_collection_lines(deck_text)
    collection = Collection(
        user_id=user.id,
        name=_infer_collection_name(name, parsed_lines),
        deck_type=_coerce_deck_type(deck_type, parsed_lines),
    )
    db.add(collection)
    _replace_collection_items(db, collection, parsed_lines)
    db.commit()
    db.refresh(collection)
    return get_collection_by_id(db, user, collection.id)


def get_collection_by_id(db: Session, user: User, collection_id: int) -> Collection:
    statement = _collection_query_for_user(user.id).where(Collection.id == collection_id)
    collection = db.execute(statement).scalar_one_or_none()
    if collection is None:
        raise CollectionNotFoundError("Collection not found.")
    return collection


def list_collections(db: Session, user: User) -> list[Collection]:
    statement = _collection_query_for_user(user.id)
    return list(db.execute(statement).scalars())


def update_collection(
    db: Session,
    user: User,
    collection_id: int,
    *,
    name: str | None = None,
    deck_text: str | None = None,
    deck_type: DeckType | str | None = None,
) -> Collection:
    collection = get_collection_by_id(db, user, collection_id)

    if name is not None and name.strip():
        collection.name = name.strip()

    if deck_text is not None:
        parsed_lines = _parse_collection_lines(deck_text)
        if name is None and not collection.name.strip():
            collection.name = _infer_collection_name(None, parsed_lines)
        _replace_collection_items(db, collection, parsed_lines)
        collection.deck_type = _coerce_deck_type(deck_type, parsed_lines)
    elif deck_type is not None:
        collection.deck_type = _coerce_deck_type(deck_type, [])

    db.commit()
    db.refresh(collection)
    return get_collection_by_id(db, user, collection.id)


def delete_collection(db: Session, user: User, collection_id: int) -> None:
    collection = get_collection_by_id(db, user, collection_id)
    db.delete(collection)
    db.commit()


def get_master_collection(db: Session, user: User) -> dict:
    collections = list_collections(db, user)
    aggregated: dict[str, dict] = {}

    for collection in collections:
        for item in collection.items:
            card = item.card
            if card is None:
                continue

            bucket = aggregated.get(card.oracle_id)
            if bucket is None:
                bucket = {
                    "oracle_id": card.oracle_id,
                    "name": card.name,
                    "total_amount": 0,
                    "prints": [],
                }
                aggregated[card.oracle_id] = bucket

            bucket["total_amount"] += item.amount
            bucket["prints"].append(
                {
                    "collection_id": collection.id,
                    "collection_name": collection.name,
                    "card_id": card.id,
                    "set_code": card.set_code,
                    "collector_number": card.collector_number,
                    "amount": item.amount,
                    "zone": item.zone,
                }
            )

    return {
        "user_id": user.id,
        "collection_count": len(collections),
        "cards": sorted(aggregated.values(), key=lambda card: card["name"]),
    }
