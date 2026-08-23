from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.models.transaction import PortfolioTransaction, TransactionType

ZERO = Decimal("0")


class InsufficientSharesError(ValueError):
    def __init__(self, symbol: str, available: Decimal) -> None:
        super().__init__(f"Cannot sell {symbol}: only {float(available):g} shares are available.")


@dataclass(frozen=True)
class TaxLotState:
    source_transaction_id: UUID
    acquired_at: datetime
    original_quantity: Decimal
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
    remaining_quantity: Decimal
    cost_per_share: Decimal


def calculate_position(
    symbol: str,
    transactions: list[PortfolioTransaction],
) -> PositionState:
    realized_gain = ZERO
    lots: list[_WorkingLot] = []

    for transaction in transactions:
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
