"""Add transaction history and watchlists while preserving existing holdings.

Revision ID: 20260819_0002
Revises: 20260819_0001
Create Date: 2026-08-19
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_0002"
down_revision: str | None = "20260819_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "watchlists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_watchlist_user_name"),
    )
    op.create_index(op.f("ix_watchlists_user_id"), "watchlists", ["user_id"], unique=False)

    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("watchlist_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["watchlist_id"], ["watchlists.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("watchlist_id", "symbol", name="uq_watchlist_symbol"),
    )
    op.create_index(
        op.f("ix_watchlist_items_watchlist_id"),
        "watchlist_items",
        ["watchlist_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_watchlist_items_symbol"),
        "watchlist_items",
        ["symbol"],
        unique=False,
    )

    op.create_table(
        "portfolio_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("transaction_type", sa.String(length=20), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("price", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "transaction_type IN ('buy', 'sell', 'opening_balance')",
            name="portfolio_transaction_type",
        ),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_portfolio_transactions_portfolio_id"),
        "portfolio_transactions",
        ["portfolio_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_portfolio_transactions_symbol"),
        "portfolio_transactions",
        ["symbol"],
        unique=False,
    )
    op.create_index(
        op.f("ix_portfolio_transactions_transaction_type"),
        "portfolio_transactions",
        ["transaction_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_portfolio_transactions_occurred_at"),
        "portfolio_transactions",
        ["occurred_at"],
        unique=False,
    )

    connection = op.get_bind()
    now = datetime.now(UTC)
    users = sa.table("users", sa.column("id", sa.Uuid()))
    watchlists = sa.table(
        "watchlists",
        sa.column("id", sa.Uuid()),
        sa.column("user_id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    existing_users = connection.execute(sa.select(users.c.id)).all()
    if existing_users:
        connection.execute(
            sa.insert(watchlists),
            [
                {
                    "id": uuid4(),
                    "user_id": user_id,
                    "name": "My Watchlist",
                    "created_at": now,
                }
                for (user_id,) in existing_users
            ],
        )

    holdings = sa.table(
        "holdings",
        sa.column("portfolio_id", sa.Uuid()),
        sa.column("symbol", sa.String()),
        sa.column("quantity", sa.Numeric()),
        sa.column("average_cost", sa.Numeric()),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    transactions = sa.table(
        "portfolio_transactions",
        sa.column("id", sa.Uuid()),
        sa.column("portfolio_id", sa.Uuid()),
        sa.column("symbol", sa.String()),
        sa.column("transaction_type", sa.String()),
        sa.column("quantity", sa.Numeric()),
        sa.column("price", sa.Numeric()),
        sa.column("occurred_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    existing_holdings = connection.execute(sa.select(holdings)).mappings().all()
    if existing_holdings:
        connection.execute(
            sa.insert(transactions),
            [
                {
                    "id": uuid4(),
                    "portfolio_id": holding["portfolio_id"],
                    "symbol": holding["symbol"],
                    "transaction_type": "opening_balance",
                    "quantity": holding["quantity"],
                    "price": holding["average_cost"],
                    "occurred_at": holding["updated_at"],
                    "created_at": now,
                }
                for holding in existing_holdings
            ],
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_portfolio_transactions_occurred_at"), table_name="portfolio_transactions")
    op.drop_index(
        op.f("ix_portfolio_transactions_transaction_type"),
        table_name="portfolio_transactions",
    )
    op.drop_index(op.f("ix_portfolio_transactions_symbol"), table_name="portfolio_transactions")
    op.drop_index(
        op.f("ix_portfolio_transactions_portfolio_id"),
        table_name="portfolio_transactions",
    )
    op.drop_table("portfolio_transactions")
    op.drop_index(op.f("ix_watchlist_items_symbol"), table_name="watchlist_items")
    op.drop_index(op.f("ix_watchlist_items_watchlist_id"), table_name="watchlist_items")
    op.drop_table("watchlist_items")
    op.drop_index(op.f("ix_watchlists_user_id"), table_name="watchlists")
    op.drop_table("watchlists")
