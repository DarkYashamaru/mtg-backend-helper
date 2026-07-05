from downloaders.download_all_cards import download_all_cards_if_needed
from tools.logger import logger

def download_data():
    logger.info("Checking all_cards.json...")
    download_all_cards_if_needed()