from fastapi import APIRouter

from app.api.v1.routes import admin, auth, health, market, portfolio, watchlist

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(market.router, prefix="/api/v1", tags=["market"])
api_router.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
api_router.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])
api_router.include_router(watchlist.router, prefix="/api/v1/watchlist", tags=["watchlist"])
api_router.include_router(admin.router, prefix="/api/v1/admin", tags=["administration"])
