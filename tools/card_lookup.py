from __future__ import annotations

import re
import unicodedata


def normalize_card_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def normalize_set_code(value: str) -> str:
    return value.strip().casefold()


def normalize_collector_number(value: str) -> str:
    normalized = value.strip()
    match = re.fullmatch(r"0*(\d+)(.*)", normalized)
    if not match:
        return normalized

    number, suffix = match.groups()
    normalized_number = str(int(number)) if number else "0"
    return f"{normalized_number}{suffix}"
