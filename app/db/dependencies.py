from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Provides a database session for each request.
    """
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()