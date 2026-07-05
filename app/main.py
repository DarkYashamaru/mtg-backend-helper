from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel
import uvicorn
import re
from services.deck_processor import process_deck
import requests
from curl_cffi import requests as curl_req
from bs4 import BeautifulSoup, Tag
from services.mtg_database import *
import unicodedata
from tools.logger import logger
from scripts.download_bulk_data import download_data
from database.create_database import create_database
from scripts.import_all_data import import_all

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MTG Companion API...")

    create_database()

    # Uncomment ONLY when you want to refresh data
    logger.info("Checking downloads...")
    download_data()
    logger.info("Importing data...")
    import_all()

    #db: Session = next(get_db())

    # try:

    #     precompute_card_theme_from_edhrec(db)
    #     precompute_commander_theme_edhrec(db)
    
    # except:
    #     logger.exception("EDHREC imports failed")

    logger.info("Startup complete")

    yield

    logger.info("Shutting down...")

app = FastAPI(
    title="MTG Companion API",
    version="0.1.0",
    lifespan=lifespan,
)

# --- Pydantic Models for Data Validation ---
class DeckPayload(BaseModel):
    deck_text: str = ""


# --- Helper Functions ---
def clean_card_name(name):
    normalized = unicodedata.normalize('NFD', name)
    return "".join(c for c in normalized if unicodedata.category(c) != 'Mn').replace("’", "'")


# --- Routes ---

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/cards/id/{oracle_id}")
def card_by_id(oracle_id: str):
    try:
        card = get_card_by_id(oracle_id)
        return card
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/api/cards/name/{name:path}")
def card_by_name(name: str):
    try:
        card = get_card_by_name(name)
        return card
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/api/analyze")
def analyze(payload: DeckPayload):
    deck_text = payload.deck_text.strip()

    if not deck_text:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "deck_text is required"}
        )

    try:
        result = process_deck(deck_text)
        return {"success": True, "result": result}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.post("/api/deck-cards")
def deck_cards(payload: DeckPayload):
    deck_text = payload.deck_text.strip()

    if not deck_text:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "deck_text is required"}
        )

    try:
        cards = get_cards_bulk(deck_text)
        return {"success": True, "cards": cards}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/api/themes/by-commander/{oracle_id}")
def themes_by_card(oracle_id: str):
    try:
        themes = get_themes_by_card(oracle_id)
        return themes
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to retrieve strategy themes: {str(e)}"}
        )


@app.get("/api/advanced")
def advanced_search_route(request: Request):
    try:
        raw_qs = request.url.query
        url = f"{BASE_URL}/advanced/"
        if raw_qs:
            url = f"{url}?{raw_qs}"

        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.json()

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/api/scrape-price")
def get_card_price(name: str = Query(None)):
    if not name:
        return JSONResponse(
            status_code=400, 
            content={"error": "Missing 'name' query parameter"}
        )

    search_name = clean_card_name(name)
    url = f"https://dracostore.co/catalogo?q={curl_req.utils.quote(search_name)}&sort=price_asc"

    try:
        response = curl_req.get(url, impersonate="chrome", timeout=10)
        
        if response.status_code != 200:
            return JSONResponse(
                status_code=400,
                content={"success": False, "dracostore_status_code": response.status_code}
            )

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # --- CASE A: Direct Redirect ---
        if "/carta/" in response.url:
            price_span = soup.find('span', string=re.compile('COP'))
            if price_span:
                clean_price = price_span.text.strip().replace('$', '').replace(' COP', '').strip()
                return {"success": True, "card": name, "currency": "COP", "price": clean_price}

        # --- CASE B: Catalog Search List ---
        else:
            card_link = soup.find('a', {'aria-label': name}) or soup.find('a', {'aria-label': search_name})
            
            if card_link and isinstance(card_link.parent, Tag):
                card_container = card_link.parent
                price_span = card_container.find('span', string=re.compile('COP'))
                
                if price_span:
                    clean_price = price_span.text.strip().replace('$', '').replace(' COP', '').strip()
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)