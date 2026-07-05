from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.session import get_db
from services.users import (
    InvalidUserData,
    UserAlreadyExists,
    authenticate_user,
    create_user,
    serialize_user,
)


router = APIRouter(prefix="/api/users", tags=["users"])


class UserCreatePayload(BaseModel):
    username: str
    password: str


class UserLoginPayload(BaseModel):
    username: str
    password: str


@router.post("", status_code=201)
def create_user_route(payload: UserCreatePayload, db: Session = Depends(get_db)):
    try:
        user = create_user(db, payload.username, payload.password)
        return {"success": True, "user": serialize_user(user)}
    except InvalidUserData as e:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(e)}
        )
    except UserAlreadyExists as e:
        return JSONResponse(
            status_code=409,
            content={"success": False, "error": str(e)}
        )


@router.post("/login")
def login_user_route(payload: UserLoginPayload, request: Request, db: Session = Depends(get_db)):
    ip_address = request.client.host if request.client else None
    user = authenticate_user(db, payload.username, payload.password, ip_address=ip_address)

    if user is None:
        return JSONResponse(
            status_code=401,
            content={"success": False, "error": "Invalid username or password."}
        )

    return {"success": True, "user": serialize_user(user)}
