from sqlalchemy import inspect, text

from app.db.database import Base, engine

# Import all models here so SQLAlchemy knows about them.
from app.models.wallet import Wallet  # noqa: F401
from app.models.holding import Holding  # noqa: F401
from app.models.trade import Trade  # noqa: F401
from app.models.automation_rule import AutomationRule  # noqa: F401


def _migrate_trades_table() -> None:
    """
    Adds fee-related columns to an existing SQLite database.

    Existing trade records are preserved.

    New columns:
    - fee
    - fee_currency
    - net_value
    """

    inspector = inspect(engine)

    if "trades" not in inspector.get_table_names():
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("trades")
    }

    with engine.begin() as connection:

        if "fee" not in columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE trades
                    ADD COLUMN fee NUMERIC(24, 8)
                    NOT NULL DEFAULT 0
                    """
                )
            )

        if "fee_currency" not in columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE trades
                    ADD COLUMN fee_currency VARCHAR(20)
                    NOT NULL DEFAULT 'NGN'
                    """
                )
            )

        if "net_value" not in columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE trades
                    ADD COLUMN net_value NUMERIC(24, 2)
                    NOT NULL DEFAULT 0
                    """
                )
            )

        # Existing trades pre-date fee tracking.
        # Their previous total_value is treated as their
        # historical net value because we cannot reconstruct
        # historical exchange fees reliably.
        connection.execute(
            text(
                """
                UPDATE trades
                SET net_value = total_value
                WHERE net_value = 0
                """
            )
        )


def _migrate_automation_rules_table() -> None:
    """
    Adds automated position-tracking columns to an existing
    automation_rules table.

    Existing automation rules are preserved.

    New columns:
    - position_open
    - entry_price
    - entry_quantity
    - entry_cost
    - target_sell_price
    """

    inspector = inspect(engine)

    if "automation_rules" not in inspector.get_table_names():
        return

    columns = {
        column["name"]
        for column in inspector.get_columns(
            "automation_rules"
        )
    }

    with engine.begin() as connection:

        if "position_open" not in columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE automation_rules
                    ADD COLUMN position_open BOOLEAN
                    NOT NULL DEFAULT 0
                    """
                )
            )

        if "entry_price" not in columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE automation_rules
                    ADD COLUMN entry_price NUMERIC(32, 8)
                    """
                )
            )

        if "entry_quantity" not in columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE automation_rules
                    ADD COLUMN entry_quantity NUMERIC(32, 16)
                    """
                )
            )

        if "entry_cost" not in columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE automation_rules
                    ADD COLUMN entry_cost NUMERIC(32, 8)
                    """
                )
            )

        if "target_sell_price" not in columns:
            connection.execute(
                text(
                    """
                    ALTER TABLE automation_rules
                    ADD COLUMN target_sell_price NUMERIC(32, 8)
                    """
                )
            )


def init_db() -> None:
    """
    Create all database tables and apply lightweight
    SQLite schema migrations.
    """

    Base.metadata.create_all(bind=engine)

    _migrate_trades_table()

    _migrate_automation_rules_table()