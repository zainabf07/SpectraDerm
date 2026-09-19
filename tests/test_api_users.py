from fastapi.testclient import TestClient
from spectraderm.api.app import create_app
from spectraderm.api.config import APISettings
def client(tmp_path): return TestClient(create_app(APISettings(storage_root=tmp_path)))
def test_create_get_and_update_user_consent(tmp_path):
    api=client(tmp_path); user=api.post("/api/v1/users",json={"general_consent":True}).json()
    assert user["user_id"].startswith("usr_") and user["location_consent"] is False
    assert api.get(f"/api/v1/users/{user['user_id']}").status_code==200
    assert api.patch(f"/api/v1/users/{user['user_id']}/consent",json={"location_consent":True}).json()["general_consent"] is True
def test_missing_user_and_malformed_request_are_safe(tmp_path):
    api=client(tmp_path)
    assert api.get("/api/v1/users/missing").status_code==404
    assert api.post("/api/v1/users",json={"general_consent":"yes"}).status_code==422
