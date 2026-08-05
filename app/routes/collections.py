from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.session import get_db
from models.collection import DeckType
from models.users import User
from services.auth import get_current_user
from services.collections import (
    CollectionCardLookupError,
    CollectionNotFoundError,
    CollectionParseError,
    create_collection_from_deck_text,
    delete_collection,
    get_collection_by_id,
    get_master_collection,
    list_collections,
    serialize_collection,
    update_collection,
)


router = APIRouter(prefix="/api/collections", tags=["collections"])


class CollectionCreatePayload(BaseModel):
    name: Optional[str] = None
    deck_text: str
    deck_type: Optional[DeckType] = None


class CollectionUpdatePayload(BaseModel):
    name: Optional[str] = None
    deck_text: Optional[str] = None
    deck_type: Optional[DeckType] = None


@router.get("")
def list_user_collections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    collections = list_collections(db, current_user)
    return {
        "success": True,
        "collections": [serialize_collection(item, include_items=False) for item in collections],
    }


@router.get("/master")
def get_master_user_collection(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"success": True, "collection": get_master_collection(db, current_user)}


@router.get("/{collection_id}")
def get_user_collection(
    collection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        collection = get_collection_by_id(db, current_user, collection_id)
        return {"success": True, "collection": serialize_collection(collection)}
    except CollectionNotFoundError as exc:
        return JSONResponse(status_code=404, content={"success": False, "error": str(exc)})


@router.post("", status_code=201)
def create_user_collection(
    payload: CollectionCreatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        collection = create_collection_from_deck_text(
            db,
            current_user,
            payload.name,
            payload.deck_text,
            deck_type=payload.deck_type,
        )
        return {"success": True, "collection": serialize_collection(collection)}
    except (CollectionParseError, CollectionCardLookupError) as exc:
        return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})


@router.put("/{collection_id}")
def update_user_collection(
    collection_id: int,
    payload: CollectionUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        collection = update_collection(
            db,
            current_user,
            collection_id,
            name=payload.name,
            deck_text=payload.deck_text,
            deck_type=payload.deck_type,
        )
        return {"success": True, "collection": serialize_collection(collection)}
    except CollectionNotFoundError as exc:
        return JSONResponse(status_code=404, content={"success": False, "error": str(exc)})
    except (CollectionParseError, CollectionCardLookupError) as exc:
        return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})


@router.delete("/{collection_id}")
def delete_user_collection(
    collection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        delete_collection(db, current_user, collection_id)
        return {"success": True}
    except CollectionNotFoundError as exc:
        return JSONResponse(status_code=404, content={"success": False, "error": str(exc)})
