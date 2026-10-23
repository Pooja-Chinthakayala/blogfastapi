import os
os.environ["DATABASE_URL"] = "sqlite:///./test_blog.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-tests-only"
os.environ["UPLOAD_DIR"] = "test_uploads"

import pytest
from fastapi.testclient import TestClient
from app.database import Base, engine
from app.main import app

@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def register_user(client, name, email, password="Password123", role="reader"):
    response = client.post("/auth/register", json={
        "name": name, "email": email, "password": password, "role": role
    })
    assert response.status_code == 201, response.text
    return response.json()

def token_for(client, email, password="Password123"):
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}
