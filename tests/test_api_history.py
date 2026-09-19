from fastapi.testclient import TestClient
from spectraderm.api.app import create_app
from spectraderm.api.config import APISettings
def setup(tmp_path):
 api=TestClient(create_app(APISettings(storage_root=tmp_path))); u=api.post("/api/v1/users",json={}).json()["user_id"]
 api.post(f"/api/v1/users/{u}/scans",json={"image_reference":"one"}); api.post(f"/api/v1/users/{u}/scans",json={"image_reference":"two"}); return api,u
def test_history_and_timeline_use_scan_storage(tmp_path):
 api,u=setup(tmp_path); assert len(api.get(f"/api/v1/users/{u}/history").json()["timeline"])==2
 assert api.get(f"/api/v1/users/{u}/timeline").status_code==200
def test_missing_history_user_is_not_found(tmp_path): assert TestClient(create_app(APISettings(storage_root=tmp_path))).get("/api/v1/users/missing/history").status_code==404
