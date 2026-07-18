import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.services.seed import seed_database


@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    Base.metadata.create_all(engine)
    with SessionLocal() as db: seed_database(db, reset=True)

@pytest.fixture()
def client(): return TestClient(app)

@pytest.fixture()
def token(client):
    response=client.post("/api/v1/auth/login",json={"email":"admin@buildtwin.local","password":"BuildTwin123!"})
    assert response.status_code==200
    return response.json()["access_token"]

@pytest.fixture()
def headers(token): return {"Authorization":f"Bearer {token}"}
