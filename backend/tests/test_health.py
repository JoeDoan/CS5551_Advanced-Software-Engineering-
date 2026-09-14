from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check_endpoint():
    """Verify GET /api/v1/health returns 200 OK and valid status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert "timestamp" in data


def test_root_endpoint():
    """Verify root / returns 200 OK with docs links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "docs" in data
