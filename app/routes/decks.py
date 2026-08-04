from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from services.deck_processor import process_deck
from services.mtg_database import get_cards_bulk


router = APIRouter(prefix="/api", tags=["decks"])


class DeckPayload(BaseModel):
    deck_text: str = ""


@router.post("/analyze")
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


@router.post("/deck-cards")
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
