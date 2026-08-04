from sqlalchemy import text
from database.base import Base
from database.session import engine, get_engine

# import all models
from models.card import *
from models.collection import *
from models.users import *


def create_database():
    # 1. Create the structural tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # 2. Optimize the file structure via Vacuum
    vacuum_database()


def vacuum_database():
    """Defragments and shrinks the SQLite file on disk safely from Python."""
    dynamic_engine = get_engine()
    
    with dynamic_engine.connect() as conn:
        # We must explicitly bypass the transaction wrapper for VACUUM to work
        conn.execution_options(isolation_level="AUTOCOMMIT").execute(text("VACUUM;"))