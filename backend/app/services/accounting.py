from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cash_event import CashEvent, CashEventType
from app.models.corporate_action import CorporateAction
from app.models.portfolio import Portfolio
from app.models.transaction import PortfolioTransaction, TransactionType
from app.providers.market import MarketDataError, MarketDataProvider
from app.schemas.portfolio import (
    AccountingSummaryResponse,
    CashEventCreateRequest,
    CashEventCreateResponse,
    CashEventResponse,
    HoldingValuationResponse,
    PortfolioValuationResponse,
)
from app.services.ledger import calculate_position

ZERO = Decimal("0")


class InsufficientCashError(ValueError):
    def __init__(self, required: Decimal, available: Decimal) -> None:
        super().__init__(
            f"Insufficient cash: ${float(required):,.2f} is required but "
            f"${float(available):,.2f} is available."
        )


def _cash_event_response(event: CashEvent) -> CashEventResponse:
    return CashEventResponse(
        id=event.id,
        event_type=event.event_type,
        amount=float(event.amount),
        symbol=event.symbol,
        occurred_at=event.occurred_at,
    )


def _all_transactions(database: Session, portfolio_id: UUID) -> list[PortfolioTransaction]:
    return list(
        database.scalars(
            select(PortfolioTransaction)
            .where(
                PortfolioTransaction.portfolio_id == portfolio_id,
                PortfolioTransaction.voided_at.is_(None),
            )
            .order_by(PortfolioTransaction.occurred_at, PortfolioTransaction.created_at)
        )
    )


def _all_cash_events(database: Session, portfolio_id: UUID) -> list[CashEvent]:
    return list(
        database.scalars(
            select(CashEvent)
            .where(CashEvent.portfolio_id == portfolio_id)
            .order_by(CashEvent.occurred_at, CashEvent.created_at)
        )
    )


def _all_corporate_actions(database: Session, portfolio_id: UUID) -> list[CorporateAction]:
    return list(
        database.scalars(
            select(CorporateAction)
            .where(
                CorporateAction.portfolio_id == portfolio_id,
                CorporateAction.voided_at.is_(None),
            )
            .order_by(CorporateAction.occurred_at, CorporateAction.created_at)
        )
    )


def list_cash_events(
    database: Session,
    portfolio_id: UUID,
    *,
    limit: int = 100,
) -> list[CashEventResponse]:
    events = database.scalars(
        select(CashEvent)
        .where(CashEvent.portfolio_id == portfolio_id)
        .order_by(CashEvent.occurred_at.desc(), CashEvent.created_at.desc())
        .limit(limit)
    )
    return [_cash_event_response(event) for event in events]


def _transaction_cash_delta(transaction: PortfolioTransaction) -> Decimal:
    gross = transaction.quantity * transaction.price
    if transaction.transaction_type == TransactionType.SELL:
        return gross - transaction.fee
    return -(gross + transaction.fee)


def _cash_event_delta(event: CashEvent) -> Decimal:
    if event.event_type == CashEventType.WITHDRAWAL:
        return -event.amount
    return event.amount


def validate_cash_timeline(database: Session, portfolio_id: UUID) -> None:
    timeline: list[tuple[datetime, int, Decimal]] = []
    for event in _all_cash_events(database, portfolio_id):
        priority = 3 if event.event_type == CashEventType.WITHDRAWAL else 0
        timeline.append((event.occurred_at, priority, _cash_event_delta(event)))
    for transaction in _all_transactions(database, portfolio_id):
        priority = 1 if transaction.transaction_type == TransactionType.SELL else 2
        timeline.append((transaction.occurred_at, priority, _transaction_cash_delta(transaction)))

    balance = ZERO
    def sort_key(item: tuple[datetime, int, Decimal]) -> tuple[float, int]:
        occurred_at = item[0]
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=UTC)
        return occurred_at.timestamp(), item[1]

    for _, _, delta in sorted(timeline, key=sort_key):
        previous_balance = balance
        balance += delta
        if balance < ZERO:
            raise InsufficientCashError(required=-delta, available=previous_balance)


def calculate_accounting_summary(
    database: Session,
    portfolio_id: UUID,
) -> AccountingSummaryResponse:
    transactions = _all_transactions(database, portfolio_id)
    corporate_actions = _all_corporate_actions(database, portfolio_id)
    cash_events = _all_cash_events(database, portfolio_id)
    cash_balance = sum((_transaction_cash_delta(item) for item in transactions), ZERO)
    cash_balance += sum((_cash_event_delta(item) for item in cash_events), ZERO)
    net_contributions = sum(
        (
            -event.amount
            if event.event_type == CashEventType.WITHDRAWAL
            else event.amount
            for event in cash_events
            if event.event_type
            in {CashEventType.DEPOSIT, CashEventType.WITHDRAWAL, CashEventType.OPENING_BALANCE}
        ),
        ZERO,
    )
    dividend_income = sum(
        (event.amount for event in cash_events if event.event_type == CashEventType.DIVIDEND),
        ZERO,
    )
    trade_fees = sum((transaction.fee for transaction in transactions), ZERO)

    realized_gain = ZERO
    symbols = sorted(
        {transaction.symbol for transaction in transactions}
        | {action.symbol for action in corporate_actions}
    )
    for symbol in symbols:
        symbol_transactions = [item for item in transactions if item.symbol == symbol]
        symbol_actions = [item for item in corporate_actions if item.symbol == symbol]
        realized_gain += calculate_position(
            symbol,
            symbol_transactions,
            symbol_actions,
        ).realized_gain

    return AccountingSummaryResponse(
        cash_balance=round(float(cash_balance), 2),
        net_contributions=round(float(net_contributions), 2),
        dividend_income=round(float(dividend_income), 2),
        realized_gain=round(float(realized_gain), 2),
        trade_fees=round(float(trade_fees), 2),
    )


def record_cash_event(
    database: Session,
    portfolio: Portfolio,
    request: CashEventCreateRequest,
) -> CashEventCreateResponse:
    database.scalar(select(Portfolio.id).where(Portfolio.id == portfolio.id).with_for_update())
    occurred_at = request.occurred_at or datetime.now(UTC)
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)
    else:
        occurred_at = occurred_at.astimezone(UTC)

    event = CashEvent(
        portfolio_id=portfolio.id,
        event_type=CashEventType(request.event_type),
        amount=Decimal(str(request.amount)),
        symbol=request.symbol.strip().upper() if request.symbol else None,
        occurred_at=occurred_at,
    )
    database.add(event)
    try:
        database.flush()
        validate_cash_timeline(database, portfolio.id)
        database.commit()
    except InsufficientCashError:
        database.rollback()
        raise

    database.refresh(event)
    return CashEventCreateResponse(
        cash_event=_cash_event_response(event),
        accounting=calculate_accounting_summary(database, portfolio.id),
    )


def get_portfolio_valuation(
    database: Session,
    portfolio: Portfolio,
    provider: MarketDataProvider,
) -> PortfolioValuationResponse:
    accounting = calculate_accounting_summary(database, portfolio.id)
    holdings: list[HoldingValuationResponse] = []
    quote_times: list[datetime] = []
    complete = True
    market_value_total = ZERO

    for holding in portfolio.holdings:
        quantity = Decimal(holding.quantity)
        average_cost = Decimal(holding.average_cost)
        cost_basis = quantity * average_cost
        try:
            quote = provider.get_summary(holding.symbol)
            if quote.currency != "USD":
                raise ValueError(f"{quote.currency} valuation is not supported yet.")
            current_price = Decimal(str(quote.price))
            market_value = quantity * current_price
            unrealized_gain = market_value - cost_basis
            market_value_total += market_value
            quote_times.append(quote.as_of)
            holdings.append(
                HoldingValuationResponse(
                    symbol=holding.symbol,
                    quantity=float(quantity),
                    average_cost=float(average_cost),
                    cost_basis=round(float(cost_basis), 2),
                    current_price=float(current_price),
                    market_value=round(float(market_value), 2),
                    unrealized_gain=round(float(unrealized_gain), 2),
                    change_percent=quote.change_percent,
                    as_of=quote.as_of,
                    source=quote.source,
                    error=None,
                )
            )
        except (MarketDataError, ValueError) as error:
            complete = False
            holdings.append(
                HoldingValuationResponse(
                    symbol=holding.symbol,
                    quantity=float(quantity),
                    average_cost=float(average_cost),
                    cost_basis=round(float(cost_basis), 2),
                    current_price=None,
                    market_value=None,
                    unrealized_gain=None,
                    change_percent=None,
                    as_of=None,
                    source=None,
                    error=str(error),
                )
            )

    as_of = max(quote_times, default=datetime.now(UTC))
    if not complete:
        return PortfolioValuationResponse(
            accounting=accounting,
            holdings=holdings,
            holdings_market_value=None,
            total_value=None,
            total_return=None,
            total_return_percent=None,
            is_complete=False,
            as_of=as_of,
        )

    total_value = market_value_total + Decimal(str(accounting.cash_balance))
    net_contributions = Decimal(str(accounting.net_contributions))
    total_return = total_value - net_contributions
    return PortfolioValuationResponse(
        accounting=accounting,
        holdings=holdings,
        holdings_market_value=round(float(market_value_total), 2),
        total_value=round(float(total_value), 2),
        total_return=round(float(total_return), 2),
        total_return_percent=(
            round(float(total_return / net_contributions * Decimal("100")), 2)
            if net_contributions > ZERO
            else None
        ),
        is_complete=True,
        as_of=as_of,
    )
