from __future__ import annotations

import requests

BASE_URL = "http://127.0.0.1:20011/api"


def get_cards_bulk(deck_text: str) -> list[dict]:
    response = requests.post(
        f"{BASE_URL}/cards/bulk",
        json={"decklist": deck_text},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_themes_by_card(oracle_id: str) -> list[dict]:
    response = requests.get(
        f"{BASE_URL}/themes/by-commander/{oracle_id}",
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_card_by_id(oracle_id: str) -> dict:
    response = requests.get(
        f"{BASE_URL}/cards/id/{oracle_id}",
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_card_by_name(name: str) -> dict:
    response = requests.get(
        f"{BASE_URL}/cards/by-name",
        params={"name": name},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def advanced_search(
    *,
    name: str | None = None,
    colors: list[str] | None = None,
    exact_colors: bool = False,
    tags: list[str] | None = None,
    exclude_tags: list[str] | None = None,
    card_type: str | None = None,
    oracle_text: list[str] | None = None,
    exclude_oracle_text: list[str] | None = None,
) -> list[dict]:
    params: list[tuple[str, str]] = []

    if name:
        params.append(("name", name))

    if exact_colors:
        params.append(("exact_colors", "true"))

    if card_type:
        params.append(("card_type", card_type))

    for color in colors or []:
        params.append(("colors", color))

    for tag in tags or []:
        params.append(("tags", tag))

    for tag in exclude_tags or []:
        params.append(("exclude_tags", tag))

    for text in oracle_text or []:
        params.append(("oracle_text", text))

    for text in exclude_oracle_text or []:
        params.append(("exclude_oracle_text", text))

    response = requests.get(
        f"{BASE_URL}/advanced/",
        params=params,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()