from fastapi.testclient import TestClient

from fyndit_helper.api import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_reports_the_loaded_docs():
    payload = client.get("/health").json()

    # A lower bound, not an exact number: when a page is added the test must not
    # fail. It must fail when the corpus goes missing.
    assert payload["documents"] >= 38
    assert payload["words"] > 19_000
    assert payload["characters"] > 118_000
    assert payload["estimated_tokens"] > 32_000


def test_swagger_is_available():
    assert client.get("/docs").status_code == 200


def test_openapi_schema_is_valid():
    schema = client.get("/openapi.json").json()

    assert "/health" in schema["paths"]
