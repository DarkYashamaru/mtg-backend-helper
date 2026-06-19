import re

from services.cache import (
    get_connection,
    init_db,
    get_cached_card,
    save_card,
    normalize_name
)

from services.scryfall import fetch_card

from services.formatter import (
    format_card,
    build_output
)

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


def process_deck(deck_text):

    lines = []
    deck_format = []

    for line in deck_text.splitlines():

        if line.strip():

            lines.append(line.strip())

    cleaned_lines = []

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

        cleaned_line = f"{count} {name}"

        cleaned_lines.append(cleaned_line)

        normalized = normalize_name(name)

        deck_format.append("card_detail")

        if normalized not in seen_cards:
            seen_cards.add(normalized)
            unique_cards[name] = None

    formatted_cards = []

    conn = get_connection()

    try:
        init_db(conn)

        for name in unique_cards:
            cached_card, was_cached = get_cached_card(conn, name)

            if was_cached:
                print(f"Cache hit: {name}")

                formatted_cards.append(
                    format_card(cached_card)
                )

                continue

            print(f"Fetching: {name}")

            card_json = fetch_card(name)

            save_card(conn, name, card_json)

            formatted_cards.append(
                format_card(card_json)
            )

    finally:
        conn.close()

    return build_output(
        deck_format,
        cleaned_lines,
        formatted_cards
    )
