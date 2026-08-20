"""Add trade fees and a cash-event ledger with legacy funding.

Revision ID: 20260819_0003
Revises: 20260819_0002
Create Date: 2026-08-19
"""

from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_0003"
down_revision: str | None = "20260819_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "portfolio_transactions",
        sa.Column(
            "fee",
            sa.Numeric(precision=18, scale=4),
            server_default="0",
            nullable=False,
        ),
    )
    op.create_table(
        "cash_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('deposit', 'withdrawal', 'dividend', 'opening_balance')",
            name="cash_event_type",
        ),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cash_events_portfolio_id"), "cash_events", ["portfolio_id"])
    op.create_index(op.f("ix_cash_events_event_type"), "cash_events", ["event_type"])
    op.create_index(op.f("ix_cash_events_symbol"), "cash_events", ["symbol"])
    op.create_index(op.f("ix_cash_events_occurred_at"), "cash_events", ["occurred_at"])

    connection = op.get_bind()
    transactions = sa.table(
        "portfolio_transactions",
        sa.column("portfolio_id", sa.Uuid()),
        sa.column("transaction_type", sa.String()),
        sa.column("quantity", sa.Numeric()),
        sa.column("price", sa.Numeric()),
        sa.column("occurred_at", sa.DateTime(timezone=True)),
    )
    cash_events = sa.table(
        "cash_events",
        sa.column("id", sa.Uuid()),
        sa.column("portfolio_id", sa.Uuid()),
        sa.column("event_type", sa.String()),
        sa.column("amount", sa.Numeric()),
        sa.column("symbol", sa.String()),
        sa.column("occurred_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    transactions_by_portfolio: dict[object, list[dict]] = defaultdict(list)
    rows = connection.execute(sa.select(transactions)).mappings().all()
    for transaction in rows:
        transactions_by_portfolio[transaction["portfolio_id"]].append(dict(transaction))

    now = datetime.now(UTC)
    opening_events = []
    for portfolio_id, portfolio_transactions in transactions_by_portfolio.items():
        ordered = sorted(portfolio_transactions, key=lambda item: item["occurred_at"])
        cash_balance = Decimal("0")
        lowest_balance = Decimal("0")
        for transaction in ordered:
            value = Decimal(transaction["quantity"]) * Decimal(transaction["price"])
            cash_balance += value if transaction["transaction_type"] == "sell" else -value
            lowest_balance = min(lowest_balance, cash_balance)
        required_funding = -lowest_balance
        if required_funding > 0:
            opening_events.append(
                {
                    "id": uuid4(),
                    "portfolio_id": portfolio_id,
                    "event_type": "opening_balance",
                    "amount": required_funding,
                    "symbol": None,
                    "occurred_at": ordered[0]["occurred_at"],
                    "created_at": now,
                }
            )
    if opening_events:
        connection.execute(sa.insert(cash_events), opening_events)


def downgrade() -> None:
    op.drop_index(op.f("ix_cash_events_occurred_at"), table_name="cash_events")
    op.drop_index(op.f("ix_cash_events_symbol"), table_name="cash_events")
    op.drop_index(op.f("ix_cash_events_event_type"), table_name="cash_events")
    op.drop_index(op.f("ix_cash_events_portfolio_id"), table_name="cash_events")
    op.drop_table("cash_events")
    op.drop_column("portfolio_transactions", "fee")
