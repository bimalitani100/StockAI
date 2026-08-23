from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.cash_event import CashEventType
from app.models.transaction import TransactionType
from app.schemas.auth import UserResponse


class HoldingResponse(BaseModel):
    id: UUID
    symbol: str
    quantity: float
    average_cost: float
    total_cost: float
    updated_at: datetime


class PortfolioResponse(BaseModel):
    id: UUID
    name: str
    holdings: list[HoldingResponse]
    total_cost: float


class TransactionCreateRequest(BaseModel):
    transaction_type: Literal["buy", "sell"]
    symbol: str = Field(min_length=1, max_length=10, pattern=r"^[A-Za-z][A-Za-z0-9.-]*$")
    quantity: float = Field(gt=0, le=1_000_000_000)
    price: float = Field(gt=0, le=1_000_000_000)
    fee: float = Field(default=0, ge=0, le=1_000_000)
    occurred_at: datetime | None = None


class TransactionResponse(BaseModel):
    id: UUID
    symbol: str
    transaction_type: TransactionType
    quantity: float
    price: float
    fee: float
    total_value: float
    cash_effect: float
    occurred_at: datetime
    voided_at: datetime | None
    void_reason: str | None


class TransactionCorrectionRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def reason_must_explain_the_correction(cls, value: str) -> str:
        reason = value.strip()
        if len(reason) < 3:
            raise ValueError("A correction reason must contain at least 3 characters.")
        return reason


class TaxLotResponse(BaseModel):
    source_transaction_id: UUID
    symbol: str
    acquired_at: datetime
    original_quantity: float
    remaining_quantity: float
    cost_per_share: float
    cost_basis: float


class TaxLotInventoryResponse(BaseModel):
    policy: Literal["fifo"] = "fifo"
    lots: list[TaxLotResponse]


class CashEventCreateRequest(BaseModel):
    event_type: Literal["deposit", "withdrawal", "dividend"]
    amount: float = Field(gt=0, le=1_000_000_000)
    symbol: str | None = Field(
        default=None,
        min_length=1,
        max_length=10,
        pattern=r"^[A-Za-z][A-Za-z0-9.-]*$",
    )
    occurred_at: datetime | None = None

    @model_validator(mode="after")
    def dividend_requires_symbol(self):
        if self.event_type == "dividend" and self.symbol is None:
            raise ValueError("A dividend requires a ticker symbol.")
        return self


class CashEventResponse(BaseModel):
    id: UUID
    event_type: CashEventType
    amount: float
    symbol: str | None
    occurred_at: datetime


class AccountingSummaryResponse(BaseModel):
    cash_balance: float
    net_contributions: float
    dividend_income: float
    realized_gain: float
    trade_fees: float


class TransactionCreateResponse(BaseModel):
    transaction: TransactionResponse
    portfolio: PortfolioResponse
    accounting: AccountingSummaryResponse


class TransactionCorrectionResponse(BaseModel):
    transaction: TransactionResponse
    portfolio: PortfolioResponse
    accounting: AccountingSummaryResponse


class CashEventCreateResponse(BaseModel):
    cash_event: CashEventResponse
    accounting: AccountingSummaryResponse


class HoldingValuationResponse(BaseModel):
    symbol: str
    quantity: float
    average_cost: float
    cost_basis: float
    current_price: float | None
    market_value: float | None
    unrealized_gain: float | None
    change_percent: float | None
    as_of: datetime | None
    source: str | None
    error: str | None


class PortfolioValuationResponse(BaseModel):
    accounting: AccountingSummaryResponse
    holdings: list[HoldingValuationResponse]
    holdings_market_value: float | None
    total_value: float | None
    total_return: float | None
    total_return_percent: float | None
    is_complete: bool
    as_of: datetime


class AdminUserSummary(BaseModel):
    user: UserResponse
    holding_count: int
    total_cost: float


class AdminPortfolioResponse(BaseModel):
    user: UserResponse
    portfolio: PortfolioResponse
    transactions: list[TransactionResponse]
    cash_events: list[CashEventResponse]
    accounting: AccountingSummaryResponse
    audited_at: datetime


class AuditLogResponse(BaseModel):
    id: UUID
    admin_email: str
    target_email: str | None
    action: str
    created_at: datetime
