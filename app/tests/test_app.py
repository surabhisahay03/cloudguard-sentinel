from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ["ok", "error"]  # This checks that the key exists


def test_predict():
    response = client.get("/predict")
    assert response.status_code == 200
