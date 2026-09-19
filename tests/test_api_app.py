from fastapi.testclient import TestClient
from spectraderm.api.app import create_app
from spectraderm.api.config import APISettings
from spectraderm.api.dependencies import ServiceContainer

def client(tmp_path): return TestClient(create_app(APISettings(storage_root=tmp_path)))
def test_app_factory_health_and_openapi(tmp_path):
    api = client(tmp_path)
    assert api.get("/health").json() == {"status": "ok"}
    assert api.get("/openapi.json").status_code == 200
def test_all_api_route_groups_are_registered(tmp_path):
    paths = client(tmp_path).get("/openapi.json").json()["paths"]
    assert "/api/v1/users" in paths and "/api/v1/scans/{scan_id}/analyze" in paths and "/api/v1/scans/{scan_id}/report" in paths
def test_configuration_loads_from_explicit_settings(tmp_path):
    app = create_app(APISettings(environment="test", storage_root=tmp_path, cors_origins=("https://example.test",)))
    assert app.state.settings.environment == "test"
def test_local_frontend_preflight_is_handled_by_cors_middleware(tmp_path):
    for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
        response = client(tmp_path).options("/api/v1/users", headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        })
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
        assert "POST" in response.headers["access-control-allow-methods"]
        assert "OPTIONS" in response.headers["access-control-allow-methods"]
        assert "content-type" in response.headers["access-control-allow-headers"].lower()
def test_dependency_container_is_overrideable(tmp_path):
    container = ServiceContainer(APISettings(storage_root=tmp_path))
    assert create_app(APISettings(storage_root=tmp_path), container).state.services is container

def test_error_handler_uses_integer_status_and_consistent_envelope(tmp_path):
    response = client(tmp_path).get("/api/v1/users/missing")
    assert response.status_code == 404
    assert response.json() == {"error": {"code": "USER_NOT_FOUND", "message": "User was not found."}}
