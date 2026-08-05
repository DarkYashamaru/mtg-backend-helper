from enum import Enum
from typing import List, Optional
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from database.base import Base

class ImageType(str, Enum):
    SMALL = "small"
    NORMAL = "normal"
    LARGE = "large"
    PNG = "png"
    ART_CROP = "art_crop"
    BORDER_CROP = "border_crop"


# 1. Main Card Table
class CardPrint(Base):
    __tablename__ = "cards"
    __table_args__ = (
        Index(
            "ix_cards_lookup_exact",
            "name_normalized",
            "set_code_normalized",
            "collector_number_normalized",
        ),
        Index(
            "ix_cards_lookup_fallback",
            "name_normalized",
            "set_code_normalized",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    oracle_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    name_normalized: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    lang: Mapped[str] = mapped_column(String, index=True)
    released_at: Mapped[str] = mapped_column(String)
    scryfall_uri: Mapped[str] = mapped_column(String)
    layout: Mapped[str] = mapped_column(String)
    
    # Extra flat fields from JSON
    rarity: Mapped[str] = mapped_column(String)
    set_code: Mapped[str] = mapped_column(String, index=True)
    set_code_normalized: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    set_name: Mapped[str] = mapped_column(String)
    collector_number: Mapped[str] = mapped_column(String)
    collector_number_normalized: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    
    # Storing prices flat on the card row since the keys are fixed and predictable
    price_usd: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    price_usd_foil: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    price_eur: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships (Fully Cascaded for deep inserts)
    faces: Mapped[List["CardPrintFace"]] = relationship("CardPrintFace", back_populates="card", cascade="all, delete-orphan")
    images: Mapped[List["CardPrintImage"]] = relationship("CardPrintImage", back_populates="card", cascade="all, delete-orphan")

    relationships: Mapped[List["CardRelationship"]] = relationship(
        "CardRelationship",
        foreign_keys="[CardRelationship.card_id]",
        back_populates="source_card",
        cascade="all, delete-orphan"
    )


# 2. Sub-faces Table (For Adventure, Split, Transform cards)
class CardPrintFace(Base):
    __tablename__ = "card_faces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[str] = mapped_column(String, ForeignKey("cards.id"), nullable=False)
    
    name: Mapped[str] = mapped_column(String)
    flavor_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    artist: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    card: Mapped["CardPrint"] = relationship("CardPrint", back_populates="faces")
    images: Mapped[List["CardPrintImage"]] = relationship("CardPrintImage", back_populates="card_face", cascade="all, delete-orphan")


# 3. Normalized Images Table
class CardPrintImage(Base):
    __tablename__ = "card_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # An image can belong directly to a Card OR to a specific CardFace (double-faced layouts)
    card_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("cards.id"), nullable=True)
    card_face_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("card_faces.id"), nullable=True)
    
    image_type: Mapped[ImageType] = mapped_column(SQLEnum(ImageType), nullable=False)
    uri: Mapped[str] = mapped_column(String, nullable=False)

    # Relationships
    card: Mapped[Optional["CardPrint"]] = relationship("CardPrint", back_populates="images")
    card_face: Mapped[Optional["CardPrintFace"]] = relationship("CardPrintFace", back_populates="images")

class CardRelationship(Base):
    __tablename__ = "card_relationships"

    card_id: Mapped[str] = mapped_column(String, ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True)
    related_id: Mapped[str] = mapped_column(String, ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True)
    component: Mapped[str] = mapped_column(String, primary_key=True)

    # Explicit directional mapping properties
    source_card: Mapped["CardPrint"] = relationship("CardPrint", foreign_keys=[card_id], back_populates="relationships")
    target_card: Mapped["CardPrint"] = relationship("CardPrint", foreign_keys=[related_id])
