from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio


class CorporateActionType(StrEnum):
    STOCK_SPLIT = "stock_split"


class CorporateAction(Base):
    __tablename__ = "corporate_actions"
    __table_args__ = (
        CheckConstraint("new_shares > 0", name="ck_corporate_action_new_shares_positive"),
        CheckConstraint("old_shares > 0", name="ck_corporate_action_old_shares_positive"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String(10), index=True)
    action_type: Mapped[CorporateActionType] = mapped_column(
        Enum(
            CorporateActionType,
            name="corporate_action_type",
            native_enum=False,
            length=30,
            create_constraint=True,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        index=True,
    )
    new_shares: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    old_shares: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    void_reason: Mapped[str | None] = mapped_column(String(500), default=None)

    portfolio: Mapped[Portfolio] = relationship(back_populates="corporate_actions")
