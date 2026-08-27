from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import CurrentUser, DatabaseSession
from app.api.v1.routes.market import get_market_data_provider
from app.providers.market import MarketDataProvider
from app.schemas.portfolio import (
    AccountingSummaryResponse,
    CashEventCreateRequest,
    CashEventCreateResponse,
    CashEventResponse,
    CorporateActionCorrectionResponse,
    CorporateActionCreateResponse,
    CorporateActionResponse,
    PortfolioResponse,
    PortfolioValuationResponse,
    TaxLotInventoryResponse,
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
    get_portfolio_valuation,
    list_cash_events,
    record_cash_event,
)
from app.services.ledger import CorporateActionReplayError, InsufficientSharesError
from app.services.portfolio import (
    CorporateActionNotCorrectableError,
    CorporateActionNotFoundError,
    TransactionNotCorrectableError,
    TransactionNotFoundError,
    get_primary_portfolio,
    get_user_portfolio,
    get_user_tax_lots,
    list_user_corporate_actions,
    list_user_transactions,
    record_transaction,
    record_stock_split,
    void_corporate_action,
    void_transaction,
)

router = APIRouter()


@router.get("", response_model=PortfolioResponse)
def portfolio(current_user: CurrentUser, database: DatabaseSession) -> PortfolioResponse:
    return get_user_portfolio(database, current_user)


@router.get("/accounting", response_model=AccountingSummaryResponse)
def accounting(
    current_user: CurrentUser,
    database: DatabaseSession,
) -> AccountingSummaryResponse:
    portfolio = get_primary_portfolio(database, current_user.id)
    return calculate_accounting_summary(database, portfolio.id)


@router.get("/cash-events", response_model=list[CashEventResponse])
def cash_events(
    current_user: CurrentUser,
    database: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
) -> list[CashEventResponse]:
    portfolio = get_primary_portfolio(database, current_user.id)
    return list_cash_events(database, portfolio.id, limit=limit)


@router.post(
    "/cash-events",
    response_model=CashEventCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_cash_event(
    request: CashEventCreateRequest,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> CashEventCreateResponse:
    portfolio = get_primary_portfolio(database, current_user.id)
    try:
        return record_cash_event(database, portfolio, request)
    except InsufficientCashError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("/valuation", response_model=PortfolioValuationResponse)
def valuation(
    current_user: CurrentUser,
    database: DatabaseSession,
    provider: MarketDataProvider = Depends(get_market_data_provider),
) -> PortfolioValuationResponse:
    portfolio = get_primary_portfolio(database, current_user.id)
    return get_portfolio_valuation(database, portfolio, provider)


@router.get("/transactions", response_model=list[TransactionResponse])
def transactions(
    current_user: CurrentUser,
    database: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
) -> list[TransactionResponse]:
    return list_user_transactions(database, current_user, limit=limit)


@router.get("/tax-lots", response_model=TaxLotInventoryResponse)
def tax_lots(
    current_user: CurrentUser,
    database: DatabaseSession,
) -> TaxLotInventoryResponse:
    return get_user_tax_lots(database, current_user)


@router.get("/corporate-actions", response_model=list[CorporateActionResponse])
def corporate_actions(
    current_user: CurrentUser,
    database: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
) -> list[CorporateActionResponse]:
    return list_user_corporate_actions(database, current_user, limit=limit)


@router.post(
    "/corporate-actions/stock-splits",
    response_model=CorporateActionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_stock_split(
    request: StockSplitCreateRequest,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> CorporateActionCreateResponse:
    try:
        return record_stock_split(database, current_user, request)
    except (CorporateActionReplayError, InsufficientSharesError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post(
    "/transactions",
    response_model=TransactionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    request: TransactionCreateRequest,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> TransactionCreateResponse:
    try:
        return record_transaction(database, current_user, request)
    except (
        CorporateActionReplayError,
        InsufficientCashError,
        InsufficientSharesError,
    ) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post(
    "/transactions/{transaction_id}/void",
    response_model=TransactionCorrectionResponse,
)
def correct_transaction(
    transaction_id: UUID,
    request: TransactionCorrectionRequest,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> TransactionCorrectionResponse:
    try:
        return void_transaction(database, current_user, transaction_id, request)
    except TransactionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found.",
        ) from error
    except (
        CorporateActionReplayError,
        TransactionNotCorrectableError,
        InsufficientCashError,
        InsufficientSharesError,
    ) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post(
    "/corporate-actions/{action_id}/void",
    response_model=CorporateActionCorrectionResponse,
)
def correct_corporate_action(
    action_id: UUID,
    request: TransactionCorrectionRequest,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> CorporateActionCorrectionResponse:
    try:
        return void_corporate_action(database, current_user, action_id, request)
    except CorporateActionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Corporate action not found.",
        ) from error
    except (
        CorporateActionNotCorrectableError,
        CorporateActionReplayError,
        InsufficientSharesError,
    ) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
