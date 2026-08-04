import re
import unicodedata

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse


router = APIRouter(prefix="/api", tags=["scrapers"])


def clean_card_name(name: str) -> str:
    normalized = unicodedata.normalize("NFD", name)
    return "".join(
        c for c in normalized if unicodedata.category(c) != "Mn"
    ).replace("\u7aae\u30fb", "'")


@router.get("/scrape-price")
def get_card_price(name: str = Query(None)):
    if not name:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing 'name' query parameter"}
        )

    search_name = clean_card_name(name)

    try:
        from bs4 import BeautifulSoup, Tag
        from curl_cffi import requests as curl_req

        url = f"https://dracostore.co/catalogo?q={curl_req.utils.quote(search_name)}&sort=price_asc"
        response = curl_req.get(url, impersonate="chrome", timeout=10)

        if response.status_code != 200:
            return JSONResponse(
                status_code=400,
                content={"success": False, "dracostore_status_code": response.status_code}
            )

        soup = BeautifulSoup(response.text, "html.parser")

        # Direct redirect to a card detail page.
        if "/carta/" in response.url:
            price_span = soup.find("span", string=re.compile("COP"))
            if price_span:
                clean_price = price_span.text.strip().replace("$", "").replace(" COP", "").strip()
                return {"success": True, "card": name, "currency": "COP", "price": clean_price}

        # Catalog search list.
        else:
            card_link = soup.find("a", {"aria-label": name}) or soup.find(
                "a", {"aria-label": search_name}
            )

            if card_link and isinstance(card_link.parent, Tag):
                card_container = card_link.parent
                price_span = card_container.find("span", string=re.compile("COP"))

                if price_span:
                    clean_price = price_span.text.strip().replace("$", "").replace(" COP", "").strip()
                    return {"success": True, "card": name, "currency": "COP", "price": clean_price}

        return JSONResponse(
            status_code=404,
            content={"error": f"Card '{name}' found, but couldn't parse the price layout."}
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to connect to store: {str(e)}"}
        )
