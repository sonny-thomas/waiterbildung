from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def get_db_engine() -> Engine:
    """Get db engine:
    This function returns the database engine.
    It is used to create the database session.
    """
    return create_engine(settings.DATABASE_URI)


db_engine = get_db_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Get db:
        This function returns the database session.
        It is used in the in any router file to get
        the database session.
    """
    database: Session = SessionLocal()
    try:
        yield database
    finally:
        database.close()
