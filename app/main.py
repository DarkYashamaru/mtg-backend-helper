from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.routes import cards, decks, health, scrapers, search, users
from database.create_database import create_database
from tools.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MTG Companion API...")

    create_database()

    # Uncomment ONLY when you want to refresh data
    from scripts.download_bulk_data import download_data
    from scripts.import_all_data import import_all

    logger.info("Checking downloads...")
    download_data()
    logger.info("Importing data...")
    import_all()

    # db: Session = next(get_db())

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

app.include_router(health.router)
app.include_router(users.router)
app.include_router(cards.router)
app.include_router(decks.router)
app.include_router(search.router)
app.include_router(scrapers.router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
