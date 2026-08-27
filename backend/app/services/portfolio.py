from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.audit import AdminAuditLog
from app.models.corporate_action import CorporateAction, CorporateActionType
from app.models.portfolio import Holding, Portfolio
from app.models.transaction import PortfolioTransaction, TransactionType
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.portfolio import (
    AdminPortfolioResponse,
    AdminUserSummary,
    AuditLogResponse,
    CorporateActionCorrectionResponse,
    CorporateActionCreateResponse,
    CorporateActionResponse,
    HoldingResponse,
    PortfolioResponse,
    TaxLotInventoryResponse,
    TaxLotResponse,
    StockSplitCreateRequest,
    TransactionCorrectionRequest,
    TransactionCorrectionResponse,
    TransactionCreateRequest,
    TransactionCreateResponse,
    TransactionResponse,
)
from app.services.accounting import (
    InsufficientCashError,
    calculate_accounting_summary,
    list_cash_events,
    validate_cash_timeline,
)
from app.services.ledger import (
    CorporateActionReplayError,
    InsufficientSharesError,
    calculate_position,
)

ZERO = Decimal("0")


class TransactionNotFoundError(LookupError):
    pass


class TransactionNotCorrectableError(ValueError):
    pass


class CorporateActionNotFoundError(LookupError):
    pass


class CorporateActionNotCorrectableError(ValueError):
    pass


def _holding_response(holding: Holding) -> HoldingResponse:
    quantity = float(holding.quantity)
    average_cost = float(holding.average_cost)
    return HoldingResponse(
        id=holding.id,
        symbol=holding.symbol,
        quantity=quantity,
        average_cost=average_cost,
        total_cost=round(quantity * average_cost, 2),
        updated_at=holding.updated_at,
    )


def _portfolio_response(portfolio: Portfolio) -> PortfolioResponse:
    holdings = [_holding_response(holding) for holding in portfolio.holdings]
    return PortfolioResponse(
        id=portfolio.id,
        name=portfolio.name,
        holdings=holdings,
        total_cost=round(sum(holding.total_cost for holding in holdings), 2),
    )


def _transaction_response(transaction: PortfolioTransaction) -> TransactionResponse:
    quantity = float(transaction.quantity)
    price = float(transaction.price)
    fee = float(transaction.fee)
    gross = quantity * price
    cash_effect = gross - fee if transaction.transaction_type == TransactionType.SELL else -(gross + fee)
    return TransactionResponse(
        id=transaction.id,
        symbol=transaction.symbol,
        transaction_type=transaction.transaction_type,
        quantity=quantity,
        price=price,
        fee=fee,
        total_value=round(gross, 2),
        cash_effect=round(cash_effect, 2),
        occurred_at=transaction.occurred_at,
        voided_at=transaction.voided_at,
        void_reason=transaction.void_reason,
    )


def _corporate_action_response(action: CorporateAction) -> CorporateActionResponse:
    new_shares = float(action.new_shares)
    old_shares = float(action.old_shares)
    return CorporateActionResponse(
        id=action.id,
        action_type=action.action_type,
        symbol=action.symbol,
        new_shares=new_shares,
        old_shares=old_shares,
        ratio=round(new_shares / old_shares, 6),
        occurred_at=action.occurred_at,
        voided_at=action.voided_at,
        void_reason=action.void_reason,
    )


def get_primary_portfolio(database: Session, user_id: UUID) -> Portfolio:
    portfolio = database.scalar(
        select(Portfolio)
        .options(selectinload(Portfolio.holdings))
        .execution_options(populate_existing=True)
        .where(Portfolio.user_id == user_id)
        .order_by(Portfolio.created_at)
    )
    if portfolio is None:
        portfolio = Portfolio(user_id=user_id, name="Primary Portfolio")
        database.add(portfolio)
        database.commit()
        database.refresh(portfolio)
    return portfolio


def get_user_portfolio(database: Session, user: User) -> PortfolioResponse:
    return _portfolio_response(get_primary_portfolio(database, user.id))


def _transactions_for_portfolio(
    database: Session,
    portfolio_id: UUID,
    *,
    limit: int = 100,
) -> list[PortfolioTransaction]:
    return list(
        database.scalars(
            select(PortfolioTransaction)
            .where(PortfolioTransaction.portfolio_id == portfolio_id)
            .order_by(
                PortfolioTransaction.occurred_at.desc(),
                PortfolioTransaction.created_at.desc(),
            )
            .limit(limit)
        )
    )


def list_user_transactions(
    database: Session,
    user: User,
    *,
    limit: int = 100,
) -> list[TransactionResponse]:
    portfolio = get_primary_portfolio(database, user.id)
    return [
        _transaction_response(transaction)
        for transaction in _transactions_for_portfolio(database, portfolio.id, limit=limit)
    ]


def _corporate_actions_for_portfolio(
    database: Session,
    portfolio_id: UUID,
    *,
    include_voided: bool = True,
    limit: int | None = None,
) -> list[CorporateAction]:
    statement = select(CorporateAction).where(CorporateAction.portfolio_id == portfolio_id)
    if not include_voided:
        statement = statement.where(CorporateAction.voided_at.is_(None))
    statement = statement.order_by(
        CorporateAction.occurred_at.desc(),
        CorporateAction.created_at.desc(),
    )
    if limit is not None:
        statement = statement.limit(limit)
    return list(database.scalars(statement))


def list_user_corporate_actions(
    database: Session,
    user: User,
    *,
    limit: int = 100,
) -> list[CorporateActionResponse]:
    portfolio = get_primary_portfolio(database, user.id)
    return [
        _corporate_action_response(action)
        for action in _corporate_actions_for_portfolio(
            database,
            portfolio.id,
            limit=limit,
        )
    ]


def _rebuild_symbol_holding(database: Session, portfolio: Portfolio, symbol: str) -> None:
    transactions = list(
        database.scalars(
            select(PortfolioTransaction)
            .where(
                PortfolioTransaction.portfolio_id == portfolio.id,
                PortfolioTransaction.symbol == symbol,
                PortfolioTransaction.voided_at.is_(None),
            )
            .order_by(
                PortfolioTransaction.occurred_at,
                PortfolioTransaction.created_at,
            )
        )
    )
    corporate_actions = _corporate_actions_for_portfolio(
        database,
        portfolio.id,
        include_voided=False,
    )
    position = calculate_position(
        symbol,
        transactions,
        [action for action in corporate_actions if action.symbol == symbol],
    )

    holding = database.scalar(
        select(Holding).where(
            Holding.portfolio_id == portfolio.id,
            Holding.symbol == symbol,
        )
    )
    if position.quantity == ZERO:
        if holding is not None:
            database.delete(holding)
        return

    if holding is None:
        holding = Holding(portfolio_id=portfolio.id, symbol=symbol)
        database.add(holding)
    holding.quantity = position.quantity
    holding.average_cost = position.average_cost


def record_transaction(
    database: Session,
    user: User,
    request: TransactionCreateRequest,
) -> TransactionCreateResponse:
    portfolio = get_primary_portfolio(database, user.id)
    database.scalar(select(Portfolio.id).where(Portfolio.id == portfolio.id).with_for_update())

    occurred_at = request.occurred_at or datetime.now(UTC)
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)
    else:
        occurred_at = occurred_at.astimezone(UTC)

    transaction = PortfolioTransaction(
        portfolio_id=portfolio.id,
        symbol=request.symbol.strip().upper(),
        transaction_type=TransactionType(request.transaction_type),
        quantity=Decimal(str(request.quantity)),
        price=Decimal(str(request.price)),
        fee=Decimal(str(request.fee)),
        occurred_at=occurred_at,
    )
    database.add(transaction)
    try:
        database.flush()
        _rebuild_symbol_holding(database, portfolio, transaction.symbol)
        validate_cash_timeline(database, portfolio.id)
        database.commit()
    except (
        CorporateActionReplayError,
        InsufficientCashError,
        InsufficientSharesError,
    ):
        database.rollback()
        raise

    database.refresh(transaction)
    return TransactionCreateResponse(
        transaction=_transaction_response(transaction),
        portfolio=_portfolio_response(get_primary_portfolio(database, user.id)),
        accounting=calculate_accounting_summary(database, portfolio.id),
    )


def get_user_tax_lots(database: Session, user: User) -> TaxLotInventoryResponse:
    portfolio = get_primary_portfolio(database, user.id)
    transactions = list(
        database.scalars(
            select(PortfolioTransaction)
            .where(
                PortfolioTransaction.portfolio_id == portfolio.id,
                PortfolioTransaction.voided_at.is_(None),
            )
            .order_by(
                PortfolioTransaction.occurred_at,
                PortfolioTransaction.created_at,
            )
        )
    )
    lots: list[TaxLotResponse] = []
    corporate_actions = _corporate_actions_for_portfolio(
        database,
        portfolio.id,
        include_voided=False,
    )
    for symbol in sorted({transaction.symbol for transaction in transactions}):
        position = calculate_position(
            symbol,
            [transaction for transaction in transactions if transaction.symbol == symbol],
            [action for action in corporate_actions if action.symbol == symbol],
        )
        lots.extend(
            TaxLotResponse(
                source_transaction_id=lot.source_transaction_id,
                symbol=symbol,
                acquired_at=lot.acquired_at,
                original_quantity=float(lot.original_quantity),
                adjusted_quantity=float(lot.adjusted_quantity),
                remaining_quantity=float(lot.remaining_quantity),
                cost_per_share=round(float(lot.cost_per_share), 4),
                cost_basis=round(float(lot.remaining_quantity * lot.cost_per_share), 2),
            )
            for lot in position.lots
        )
    return TaxLotInventoryResponse(lots=lots)


def record_stock_split(
    database: Session,
    user: User,
    request: StockSplitCreateRequest,
) -> CorporateActionCreateResponse:
    portfolio = get_primary_portfolio(database, user.id)
    database.scalar(select(Portfolio.id).where(Portfolio.id == portfolio.id).with_for_update())
    occurred_at = request.occurred_at or datetime.now(UTC)
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)
    else:
        occurred_at = occurred_at.astimezone(UTC)

    action = CorporateAction(
        portfolio_id=portfolio.id,
        action_type=CorporateActionType.STOCK_SPLIT,
        symbol=request.symbol.strip().upper(),
        new_shares=Decimal(str(request.new_shares)),
        old_shares=Decimal(str(request.old_shares)),
        occurred_at=occurred_at,
    )
    database.add(action)
    try:
        database.flush()
        _rebuild_symbol_holding(database, portfolio, action.symbol)
        database.commit()
    except (CorporateActionReplayError, InsufficientSharesError):
        database.rollback()
        raise

    database.refresh(action)
    return CorporateActionCreateResponse(
        corporate_action=_corporate_action_response(action),
        portfolio=_portfolio_response(get_primary_portfolio(database, user.id)),
    )


def void_corporate_action(
    database: Session,
    user: User,
    action_id: UUID,
    request: TransactionCorrectionRequest,
) -> CorporateActionCorrectionResponse:
    portfolio = get_primary_portfolio(database, user.id)
    database.scalar(select(Portfolio.id).where(Portfolio.id == portfolio.id).with_for_update())
    action = database.scalar(
        select(CorporateAction).where(
            CorporateAction.id == action_id,
            CorporateAction.portfolio_id == portfolio.id,
        )
    )
    if action is None:
        raise CorporateActionNotFoundError
    if action.voided_at is not None:
        raise CorporateActionNotCorrectableError("This corporate action has already been voided.")

    action.voided_at = datetime.now(UTC)
    action.void_reason = request.reason
    try:
        database.flush()
        _rebuild_symbol_holding(database, portfolio, action.symbol)
        database.commit()
    except (CorporateActionReplayError, InsufficientSharesError):
        database.rollback()
        raise

    database.refresh(action)
    return CorporateActionCorrectionResponse(
        corporate_action=_corporate_action_response(action),
        portfolio=_portfolio_response(get_primary_portfolio(database, user.id)),
    )


def void_transaction(
    database: Session,
    user: User,
    transaction_id: UUID,
    request: TransactionCorrectionRequest,
) -> TransactionCorrectionResponse:
    portfolio = get_primary_portfolio(database, user.id)
    database.scalar(select(Portfolio.id).where(Portfolio.id == portfolio.id).with_for_update())
    transaction = database.scalar(
        select(PortfolioTransaction).where(
            PortfolioTransaction.id == transaction_id,
            PortfolioTransaction.portfolio_id == portfolio.id,
        )
    )
    if transaction is None:
        raise TransactionNotFoundError
    if transaction.transaction_type == TransactionType.OPENING_BALANCE:
        raise TransactionNotCorrectableError("System opening transactions cannot be voided.")
    if transaction.voided_at is not None:
        raise TransactionNotCorrectableError("This transaction has already been voided.")

    transaction.voided_at = datetime.now(UTC)
    transaction.void_reason = request.reason.strip()
    try:
        database.flush()
        _rebuild_symbol_holding(database, portfolio, transaction.symbol)
        validate_cash_timeline(database, portfolio.id)
        database.commit()
    except (
        CorporateActionReplayError,
        InsufficientCashError,
        InsufficientSharesError,
    ):
        database.rollback()
        raise

    database.refresh(transaction)
    return TransactionCorrectionResponse(
        transaction=_transaction_response(transaction),
        portfolio=_portfolio_response(get_primary_portfolio(database, user.id)),
        accounting=calculate_accounting_summary(database, portfolio.id),
    )


def list_users_for_admin(database: Session) -> list[AdminUserSummary]:
    rows = database.execute(
        select(
            User,
            func.count(Holding.id),
            func.coalesce(func.sum(Holding.quantity * Holding.average_cost), 0),
        )
        .outerjoin(Portfolio, Portfolio.user_id == User.id)
        .outerjoin(Holding, Holding.portfolio_id == Portfolio.id)
        .group_by(User.id)
        .order_by(User.created_at.desc())
    ).all()
    return [
        AdminUserSummary(
            user=UserResponse.model_validate(user),
            holding_count=holding_count,
            total_cost=round(float(total_cost), 2),
        )
        for user, holding_count, total_cost in rows
    ]


def view_user_portfolio_as_admin(
    database: Session,
    admin: User,
    target_user_id: UUID,
) -> AdminPortfolioResponse | None:
    target = database.get(User, target_user_id)
    if target is None:
        return None

    portfolio = get_primary_portfolio(database, target.id)
    transactions = _transactions_for_portfolio(database, portfolio.id, limit=100)
    cash_events = list_cash_events(database, portfolio.id, limit=100)
    corporate_actions = _corporate_actions_for_portfolio(database, portfolio.id, limit=100)
    accounting = calculate_accounting_summary(database, portfolio.id)
    audited_at = datetime.now(UTC)
    database.add(
        AdminAuditLog(
            admin_user_id=admin.id,
            target_user_id=target.id,
            action="portfolio.view",
            created_at=audited_at,
        )
    )
    database.commit()
    return AdminPortfolioResponse(
        user=UserResponse.model_validate(target),
        portfolio=_portfolio_response(portfolio),
        transactions=[_transaction_response(transaction) for transaction in transactions],
        cash_events=cash_events,
        accounting=accounting,
        corporate_actions=[_corporate_action_response(action) for action in corporate_actions],
        audited_at=audited_at,
    )


def list_audit_logs(database: Session) -> list[AuditLogResponse]:
    admin = User.__table__.alias("admin")
    target = User.__table__.alias("target")
    rows = database.execute(
        select(
            AdminAuditLog,
            admin.c.email,
            target.c.email,
        )
        .join(admin, admin.c.id == AdminAuditLog.admin_user_id)
        .outerjoin(target, target.c.id == AdminAuditLog.target_user_id)
        .order_by(AdminAuditLog.created_at.desc())
        .limit(100)
    ).all()
    return [
        AuditLogResponse(
            id=log.id,
            admin_email=admin_email,
            target_email=target_email,
            action=log.action,
            created_at=log.created_at,
        )
        for log, admin_email, target_email in rows
    ]
