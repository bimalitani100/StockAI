"""Add correctable corporate actions for stock splits.

Revision ID: 20260826_0005
Revises: 20260823_0004
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_0005"
down_revision: str | None = "20260823_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "corporate_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("action_type", sa.String(length=30), nullable=False),
        sa.Column("new_shares", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("old_shares", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("void_reason", sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "action_type IN ('stock_split')",
            name="corporate_action_type",
        ),
        sa.CheckConstraint(
            "new_shares > 0",
            name="ck_corporate_action_new_shares_positive",
        ),
        sa.CheckConstraint(
            "old_shares > 0",
            name="ck_corporate_action_old_shares_positive",
        ),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_corporate_actions_portfolio_id"), "corporate_actions", ["portfolio_id"])
    op.create_index(op.f("ix_corporate_actions_symbol"), "corporate_actions", ["symbol"])
    op.create_index(op.f("ix_corporate_actions_action_type"), "corporate_actions", ["action_type"])
    op.create_index(op.f("ix_corporate_actions_occurred_at"), "corporate_actions", ["occurred_at"])


def downgrade() -> None:
    connection = op.get_bind()
    corporate_actions = sa.table("corporate_actions", sa.column("id", sa.Uuid()))
    if connection.scalar(sa.select(sa.func.count()).select_from(corporate_actions)):
        raise RuntimeError("Cannot downgrade while corporate actions exist.")
    op.drop_index(op.f("ix_corporate_actions_occurred_at"), table_name="corporate_actions")
    op.drop_index(op.f("ix_corporate_actions_action_type"), table_name="corporate_actions")
    op.drop_index(op.f("ix_corporate_actions_symbol"), table_name="corporate_actions")
    op.drop_index(op.f("ix_corporate_actions_portfolio_id"), table_name="corporate_actions")
    op.drop_table("corporate_actions")
