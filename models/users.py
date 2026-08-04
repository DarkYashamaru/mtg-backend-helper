from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Unique constraint prevents duplicate registrations
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    
    # Column stays named "password" for current database compatibility.
    # Code should always use password_hash and never store plain text here.
    password_hash: Mapped[str] = mapped_column("password", String, nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Metrics, Tracking & Audit Fields
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_ip: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    # Automatically drops a user's binders and decks if their account is deleted
    collections: Mapped[List["Collection"]] = relationship(
        "Collection", back_populates="user", cascade="all, delete-orphan"
    )
