from __future__ import annotations

from downloaders.scryfall_bulk_data_downloader import (  # noqa: E402
    SCRYFALL_DATA_DIR,
    BulkDataDownload,
    BulkDataFile,
    HttpSession,
    ScryfallBulkDataDownloader,
)

ALL__CARDS_TYPE = "all_cards"
ALL_CARDS_PATH = SCRYFALL_DATA_DIR / "all_cards.jsonl.gz"
ALL_CARDS_METADATA_PATH = SCRYFALL_DATA_DIR / "all_cards.meta.json"

def create_all_cards_downloader(session: HttpSession | None = None,) -> ScryfallBulkDataDownloader:

    return ScryfallBulkDataDownloader(
        bulk_data_type=ALL__CARDS_TYPE,
        file_path=ALL_CARDS_PATH,
        metadata_path=ALL_CARDS_METADATA_PATH,
        session=session,
    )

def get_all_cards_bulk_data(session: HttpSession | None = None) -> BulkDataFile:
    return create_all_cards_downloader(session).get_bulk_data()


def download_all_cards_if_needed(session: HttpSession | None = None,) -> BulkDataDownload:    
    return create_all_cards_downloader(session).download_if_needed()
