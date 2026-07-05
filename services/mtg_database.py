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