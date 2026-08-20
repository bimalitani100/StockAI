from dataclasses import dataclass
from decimal import Decimal

from app.models.transaction import PortfolioTransaction, TransactionType

ZERO = Decimal("0")


class InsufficientSharesError(ValueError):
    def __init__(self, symbol: str, available: Decimal) -> None:
        super().__init__(f"Cannot sell {symbol}: only {float(available):g} shares are available.")


@dataclass(frozen=True)
class PositionState:
    quantity: Decimal
    average_cost: Decimal
    realized_gain: Decimal


def calculate_position(
    symbol: str,
    transactions: list[PortfolioTransaction],
) -> PositionState:
    quantity = ZERO
    average_cost = ZERO
    realized_gain = ZERO

    for transaction in transactions:
        if transaction.transaction_type in {
            TransactionType.BUY,
            TransactionType.OPENING_BALANCE,
        }:
            acquisition_cost = transaction.quantity * transaction.price + transaction.fee
            total_cost = quantity * average_cost + acquisition_cost
            quantity += transaction.quantity
            average_cost = total_cost / quantity
            continue

        if transaction.quantity > quantity:
            raise InsufficientSharesError(symbol, quantity)
        proceeds = transaction.quantity * transaction.price - transaction.fee
        realized_gain += proceeds - transaction.quantity * average_cost
        quantity -= transaction.quantity
        if quantity == ZERO:
            average_cost = ZERO

    return PositionState(
        quantity=quantity,
        average_cost=average_cost,
        realized_gain=realized_gain,
    )
