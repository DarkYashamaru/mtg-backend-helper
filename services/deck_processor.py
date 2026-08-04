import re

from services.formatter import (
    format_card,
    build_output
)
from services.mtg_database import get_cards_bulk

SECTION_HEADERS = {
    "commander",
    "mainboard",
    "sideboard",
    "maybeboard",
    "artifact",
    "enchantment",
    "instant",
    "sorcery",
    "planeswalker",
    "land",
    "lands",
    "[commander]",
    "[creatures]",
    "[artifacts]",
    "[instants]",
    "[sorceries]",
    "[enchantments]",
    "[lands]",
    "[planeswalkers]",
}


def parse_line(line):
    line = line.strip()

    if not line:
        return None, None

    #
    # Format:
    # 1 Sol Ring (CMM) 123
    # 1 Sol Ring
    #
    match = re.match(
        r"^(\d+)(?:x)?\s+(.+?)(?:\s+\(|$)",
        line
    )

    if match:
        count = int(match.group(1))
        name = match.group(2).strip()

        return count, name

    #
    # Format:
    # Sol Ring
    #
    return 1, line


def normalize_name(name):
    return re.sub(r"\s+", " ", name).strip().casefold()


def process_deck(deck_text):

    lines = []
    deck_format = []

    for line in deck_text.splitlines():

        if line.strip():

            lines.append(line.strip())

    unique_cards = {}
    seen_cards = set()

    for line in lines:

        normalized_line = line.strip().casefold()

        if normalized_line in SECTION_HEADERS:
            deck_format.append(line)
            continue

        count, name = parse_line(line)

        if not name:
            continue

        normalized = normalize_name(name)

        deck_format.append("card_detail")

        if normalized not in seen_cards:
            seen_cards.add(normalized)
            unique_cards[normalized] = name

    formatted_cards = []
    lookup_names = list(unique_cards.values())
    lookup_decklist = "\n".join(f"1 {name}" for name in lookup_names)
    cards = get_cards_bulk(lookup_decklist)
    cards_by_name = {
        normalize_name(card["name"]): card
        for card in cards
    }

    for normalized_name in unique_cards:
        formatted_cards.append(
            format_card(cards_by_name.get(normalized_name))
        )

    return build_output(
        deck_format,
        formatted_cards
    )
