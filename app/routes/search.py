import requests
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from services.mtg_database import BASE_URL


router = APIRouter(prefix="/api", tags=["search"])


@router.get("/advanced")
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
