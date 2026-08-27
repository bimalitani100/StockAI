from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from app.models.corporate_action import CorporateAction, CorporateActionType
from app.models.transaction import PortfolioTransaction, TransactionType

ZERO = Decimal("0")
SHARE_QUANTUM = Decimal("0.000001")


class InsufficientSharesError(ValueError):
    def __init__(self, symbol: str, available: Decimal) -> None:
        super().__init__(f"Cannot sell {symbol}: only {float(available):g} shares are available.")


class CorporateActionReplayError(ValueError):
    pass


class CorporateActionWithoutSharesError(CorporateActionReplayError):
    def __init__(self, symbol: str) -> None:
        super().__init__(
            f"Cannot apply a stock split for {symbol}: no shares were held at that time."
        )


class UnsupportedFractionalSharesError(CorporateActionReplayError):
    def __init__(self, symbol: str) -> None:
        super().__init__(
            f"Cannot apply the stock split for {symbol}: it creates shares beyond StockAI's "
            "6-decimal precision. Cash-in-lieu is not supported yet."
        )


@dataclass(frozen=True)
class TaxLotState:
    source_transaction_id: UUID
    acquired_at: datetime
    original_quantity: Decimal
    adjusted_quantity: Decimal
    remaining_quantity: Decimal
    cost_per_share: Decimal


@dataclass(frozen=True)
class PositionState:
    quantity: Decimal
    average_cost: Decimal
    realized_gain: Decimal
    lots: tuple[TaxLotState, ...]


@dataclass
class _WorkingLot:
    source_transaction_id: UUID
    acquired_at: datetime
    original_quantity: Decimal
    adjusted_quantity: Decimal
    remaining_quantity: Decimal
    cost_per_share: Decimal


def calculate_position(
    symbol: str,
    transactions: list[PortfolioTransaction],
    corporate_actions: list[CorporateAction] | None = None,
) -> PositionState:
    realized_gain = ZERO
    lots: list[_WorkingLot] = []

    def timestamp(value: datetime) -> float:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.timestamp()

    events: list[tuple[float, int, float, str, PortfolioTransaction | CorporateAction]] = []
    for action in corporate_actions or []:
        events.append(
            (
                timestamp(action.occurred_at),
                0,
                timestamp(action.created_at or action.occurred_at),
                str(action.id),
                action,
            )
        )
    for transaction in transactions:
        events.append(
            (
                timestamp(transaction.occurred_at),
                1,
                timestamp(transaction.created_at or transaction.occurred_at),
                str(transaction.id),
                transaction,
            )
        )

    for _, _, _, _, event in sorted(events, key=lambda item: item[:4]):
        if isinstance(event, CorporateAction):
            if event.action_type != CorporateActionType.STOCK_SPLIT:
                continue
            available = sum((lot.remaining_quantity for lot in lots), ZERO)
            if available == ZERO:
                raise CorporateActionWithoutSharesError(symbol)
            ratio = event.new_shares / event.old_shares
            adjusted_lots = [
                (
                    lot,
                    lot.adjusted_quantity * ratio,
                    lot.remaining_quantity * ratio,
                    lot.cost_per_share / ratio,
                )
                for lot in lots
            ]
            if any(
                remaining_quantity.quantize(SHARE_QUANTUM) != remaining_quantity
                for _, _, remaining_quantity, _ in adjusted_lots
            ):
                raise UnsupportedFractionalSharesError(symbol)
            for lot, adjusted_quantity, remaining_quantity, cost_per_share in adjusted_lots:
                lot.adjusted_quantity = adjusted_quantity
                lot.remaining_quantity = remaining_quantity
                lot.cost_per_share = cost_per_share
            continue

        transaction = event
        if transaction.transaction_type in {
            TransactionType.BUY,
            TransactionType.OPENING_BALANCE,
        }:
            acquisition_cost = transaction.quantity * transaction.price + transaction.fee
            lots.append(
                _WorkingLot(
                    source_transaction_id=transaction.id,
                    acquired_at=transaction.occurred_at,
                    original_quantity=transaction.quantity,
                    adjusted_quantity=transaction.quantity,
                    remaining_quantity=transaction.quantity,
                    cost_per_share=acquisition_cost / transaction.quantity,
                )
            )
            continue

        available = sum((lot.remaining_quantity for lot in lots), ZERO)
        if transaction.quantity > available:
            raise InsufficientSharesError(symbol, available)

        quantity_to_sell = transaction.quantity
        consumed_cost = ZERO
        for lot in lots:
            if quantity_to_sell == ZERO:
                break
            consumed_quantity = min(lot.remaining_quantity, quantity_to_sell)
            consumed_cost += consumed_quantity * lot.cost_per_share
            lot.remaining_quantity -= consumed_quantity
            quantity_to_sell -= consumed_quantity

        proceeds = transaction.quantity * transaction.price - transaction.fee
        realized_gain += proceeds - consumed_cost

    open_lots = tuple(
        TaxLotState(
            source_transaction_id=lot.source_transaction_id,
            acquired_at=lot.acquired_at,
            original_quantity=lot.original_quantity,
            adjusted_quantity=lot.adjusted_quantity,
            remaining_quantity=lot.remaining_quantity,
            cost_per_share=lot.cost_per_share,
        )
        for lot in lots
        if lot.remaining_quantity > ZERO
    )
    quantity = sum((lot.remaining_quantity for lot in open_lots), ZERO)
    remaining_cost = sum(
        (lot.remaining_quantity * lot.cost_per_share for lot in open_lots),
        ZERO,
    )
    average_cost = remaining_cost / quantity if quantity > ZERO else ZERO

    return PositionState(
        quantity=quantity,
        average_cost=average_cost,
        realized_gain=realized_gain,
        lots=open_lots,
    )
