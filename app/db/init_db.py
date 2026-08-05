from app.db.database import Base, engine


# Import all models here so SQLAlchemy knows about them.
from app.models.wallet import Wallet  # noqa: F401
from app.models.holding import Holding # noqa: F401
from app.models.trade import Trade  # noqa: F401


def init_db() -> None:
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)