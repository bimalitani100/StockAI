from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import AdminUser, DatabaseSession
from app.schemas.portfolio import AdminPortfolioResponse, AdminUserSummary, AuditLogResponse
from app.services.portfolio import (
    list_audit_logs,
    list_users_for_admin,
    view_user_portfolio_as_admin,
)

router = APIRouter()


@router.get("/users", response_model=list[AdminUserSummary])
def users(admin: AdminUser, database: DatabaseSession) -> list[AdminUserSummary]:
    return list_users_for_admin(database)


@router.get("/users/{user_id}/portfolio", response_model=AdminPortfolioResponse)
def user_portfolio(
    user_id: UUID,
    admin: AdminUser,
    database: DatabaseSession,
) -> AdminPortfolioResponse:
    result = view_user_portfolio_as_admin(database, admin, user_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return result


@router.get("/audit-log", response_model=list[AuditLogResponse])
def audit_log(admin: AdminUser, database: DatabaseSession) -> list[AuditLogResponse]:
    return list_audit_logs(database)
