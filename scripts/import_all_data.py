from importers.card_importer import import_card_prints
from importers.import_relationships import import_relationships
from tools.logger import logger

def import_all():
    logger.info("Importing card prints...")
    imported:int = import_card_prints()
    logger.info(f"Imported {imported} card prints")

    logger.info("Importing card relationships...")
    imported = import_relationships()
    logger.info(f"Imported {imported} relationships")
