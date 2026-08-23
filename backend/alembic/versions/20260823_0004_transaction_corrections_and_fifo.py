"""Add transaction corrections and rebuild holdings using FIFO lots.

Revision ID: 20260823_0004
Revises: 20260819_0003
Create Date: 2026-08-23
"""

from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal

import sqlalchemy as sa
from alembic import op

revision: str = "20260823_0004"
down_revision: str | None = "20260819_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ZERO = Decimal("0")


def _rebuild_holding_costs(connection: sa.Connection, *, policy: str) -> None:
    transactions = sa.table(
        "portfolio_transactions",
        sa.column("portfolio_id", sa.Uuid()),
        sa.column("symbol", sa.String()),
        sa.column("transaction_type", sa.String()),
        sa.column("quantity", sa.Numeric()),
        sa.column("price", sa.Numeric()),
        sa.column("fee", sa.Numeric()),
        sa.column("occurred_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    holdings = sa.table(
        "holdings",
        sa.column("portfolio_id", sa.Uuid()),
        sa.column("symbol", sa.String()),
        sa.column("quantity", sa.Numeric()),
        sa.column("average_cost", sa.Numeric()),
    )
    grouped: dict[tuple[object, str], list[dict]] = defaultdict(list)
    rows = connection.execute(
        sa.select(transactions).order_by(transactions.c.occurred_at, transactions.c.created_at)
    ).mappings()
    for row in rows:
        grouped[(row["portfolio_id"], row["symbol"])].append(dict(row))

    for (portfolio_id, symbol), symbol_transactions in grouped.items():
        lots: list[list[Decimal]] = []
        for transaction in symbol_transactions:
            quantity = Decimal(transaction["quantity"])
            price = Decimal(transaction["price"])
            fee = Decimal(transaction["fee"] or ZERO)
            if transaction["transaction_type"] in {"buy", "opening_balance"}:
                unit_cost = (quantity * price + fee) / quantity
                lots.append([quantity, unit_cost])
                continue

            quantity_to_sell = quantity
            if policy == "fifo":
                for lot in lots:
                    consumed = min(lot[0], quantity_to_sell)
                    lot[0] -= consumed
                    quantity_to_sell -= consumed
                    if quantity_to_sell == ZERO:
                        break
            else:
                total_quantity = sum((lot[0] for lot in lots), ZERO)
                average_cost = sum((lot[0] * lot[1] for lot in lots), ZERO) / total_quantity
                lots = [[total_quantity - quantity_to_sell, average_cost]]

        remaining_quantity = sum((lot[0] for lot in lots), ZERO)
        if remaining_quantity == ZERO:
            continue
        remaining_cost = sum((lot[0] * lot[1] for lot in lots), ZERO)
        connection.execute(
            sa.update(holdings)
            .where(
                holdings.c.portfolio_id == portfolio_id,
                holdings.c.symbol == symbol,
            )
            .values(
                quantity=remaining_quantity,
                average_cost=remaining_cost / remaining_quantity,
            )
        )


def upgrade() -> None:
    op.add_column(
        "portfolio_transactions",
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "portfolio_transactions",
        sa.Column("void_reason", sa.String(length=500), nullable=True),
    )
    _rebuild_holding_costs(op.get_bind(), policy="fifo")


def downgrade() -> None:
    connection = op.get_bind()
    transactions = sa.table(
        "portfolio_transactions",
        sa.column("voided_at", sa.DateTime(timezone=True)),
    )
    if connection.scalar(
        sa.select(sa.func.count()).select_from(transactions).where(transactions.c.voided_at.is_not(None))
    ):
        raise RuntimeError("Cannot downgrade while corrected transactions exist.")
    _rebuild_holding_costs(connection, policy="weighted_average")
    op.drop_column("portfolio_transactions", "void_reason")
    op.drop_column("portfolio_transactions", "voided_at")
