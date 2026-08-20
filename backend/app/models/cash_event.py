from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio


class CashEventType(StrEnum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    DIVIDEND = "dividend"
    OPENING_BALANCE = "opening_balance"


class CashEvent(Base):
    __tablename__ = "cash_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    portfolio_id: Mapped[UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        index=True,
    )
    event_type: Mapped[CashEventType] = mapped_column(
        Enum(
            CashEventType,
            name="cash_event_type",
            native_enum=False,
            length=20,
            create_constraint=True,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    symbol: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    portfolio: Mapped[Portfolio] = relationship(back_populates="cash_events")
