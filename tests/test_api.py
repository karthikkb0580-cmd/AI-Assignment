from fastapi.testclient import TestClient

from ai_pipeline.main import app


client = TestClient(app)


def test_home():

    response = client.get("/")

    assert response.status_code == 200

    assert response.json()["application"] == (
        "AI Intelligence Pipeline"
    )


def test_health():

    response = client.get("/health")

    assert response.status_code == 200

    assert response.json()["status"] == "healthy"