import requests
import time

API_URL = "https://api.scryfall.com/cards/named"

HEADERS = {
    "User-Agent": "DeckInfoScript/1.0",
    "Accept": "application/json"
}

DELAY = 2


def fetch_card(name):
    params = {
        "exact": name
    }

    try:
        response = requests.get(
            API_URL,
            headers=HEADERS,
            params=params,
            timeout=15
        )

    except requests.RequestException as e:
        print(f"Request failed for {name}: {e}")

        return None

    if response.status_code != 200:
        print(f"Failed: {name} ({response.status_code})")

        return None

    time.sleep(DELAY)

    return response.json()
