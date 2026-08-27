import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[3] / ".env.local")


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("STOCKAI_APP_NAME", "StockAI API")
    app_version: str = os.getenv("STOCKAI_APP_VERSION", "0.8.0")
    frontend_origin: str = os.getenv("STOCKAI_FRONTEND_ORIGIN", "http://localhost:3000")
    database_url: str = os.getenv(
        "STOCKAI_DATABASE_URL",
        "postgresql+psycopg://stockai:stockai@localhost:5433/stockai",
    )
    jwt_secret_key: str = os.getenv(
        "STOCKAI_JWT_SECRET_KEY",
        "local-development-secret-change-before-deployment",
    )
    access_token_minutes: int = int(os.getenv("STOCKAI_ACCESS_TOKEN_MINUTES", "60"))
    auth_cookie_name: str = "stockai_session"
    secure_cookies: bool = os.getenv("STOCKAI_SECURE_COOKIES", "false").lower() == "true"


settings = Settings()
