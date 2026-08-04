from enum import Enum
from typing import List, Optional
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base
from models.card import CardPrint


class DeckType(str, Enum):
    STANDARD = "Standard"
    COMMANDER = "Commander"
    BINDER = "Binder"  # For non-deck collections like trade binders


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    
    # Differentiates Standard, Commander, or just a generic Binder
    deck_type: Mapped[DeckType] = mapped_column(
        SQLEnum(DeckType), default=DeckType.BINDER, nullable=False
    )
    
    # Commander-specific field: stores the Scryfall ID of the deck's Commander.
    # Set to SET NULL on delete so deleting a card print doesn't destroy the entire deck metadata row.
    commander_card_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("cards.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    items: Mapped[List["CollectionItem"]] = relationship(
        "CollectionItem", back_populates="collection", cascade="all, delete-orphan"
    )
    
    # Proper SQLAlchemy relationship pointing to the underlying CardPrint model
    commander_card: Mapped[Optional["CardPrint"]] = relationship("CardPrint")

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user: Mapped["User"] = relationship("User", back_populates="collections")


class CollectionItem(Base):
    __tablename__ = "collection_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    card_id: Mapped[str] = mapped_column(
        String, ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(Integer, default=1)
    
    # Optional metadata: separates mainboard, sideboard, maybeboard, commander, etc.
    zone: Mapped[str] = mapped_column(String, default="mainboard", index=True) 

    # Relationships
    collection: Mapped["Collection"] = relationship("Collection", back_populates="items")
    card: Mapped["CardPrint"] = relationship("CardPrint")

    # Database Guardrail: Ensures a specific card version only has ONE row per zone in a deck
    __table_args__ = (
        UniqueConstraint("collection_id", "card_id", "zone", name="uq_collection_card_zone"),
    )