from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.mtg_database import get_card_by_id, get_card_by_name, get_themes_by_card


router = APIRouter(prefix="/api", tags=["cards"])


@router.get("/cards/id/{oracle_id}")
def card_by_id(oracle_id: str):
    try:
        card = get_card_by_id(oracle_id)
        return card
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/cards/name/{name:path}")
def card_by_name(name: str):
    try:
        card = get_card_by_name(name)
        return card
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/themes/by-commander/{oracle_id}")
def themes_by_card(oracle_id: str):
    try:
        themes = get_themes_by_card(oracle_id)
        return themes
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to retrieve strategy themes: {str(e)}"}
        )
