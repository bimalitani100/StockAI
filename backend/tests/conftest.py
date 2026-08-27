import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["STOCKAI_DATABASE_URL"] = "sqlite+pysqlite://"
os.environ["STOCKAI_JWT_SECRET_KEY"] = "test-secret-not-used-outside-tests"

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models import AdminAuditLog, CorporateAction, Holding, Portfolio, User  # noqa: F401

test_engine = create_engine(
    "sqlite+pysqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


def override_get_db() -> Generator[Session, None, None]:
    with TestingSessionLocal() as database:
        yield database


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def database() -> Generator[Session, None, None]:
    with TestingSessionLocal() as session:
        yield session
