from fastapi.testclient import TestClient
from spectraderm.api.app import create_app
from spectraderm.api.config import APISettings
def setup(tmp_path):
 api=TestClient(create_app(APISettings(storage_root=tmp_path))); user=api.post("/api/v1/users",json={}).json()["user_id"]; return api,user
def test_create_retrieve_list_and_delete_scan(tmp_path):
 api,user=setup(tmp_path); scan=api.post(f"/api/v1/users/{user}/scans",json={"image_reference":"safe/image.ref"}).json()
 assert "image_reference" not in scan and api.get(f"/api/v1/scans/{scan['scan_id']}?user_id={user}").status_code==200
 assert len(api.get(f"/api/v1/users/{user}/scans").json()["scans"])==1
 assert api.delete(f"/api/v1/scans/{scan['scan_id']}?user_id={user}").status_code==204
def test_ownership_missing_and_unsafe_reference_are_rejected(tmp_path):
 api,user=setup(tmp_path); other=api.post("/api/v1/users",json={}).json()["user_id"]
 scan=api.post(f"/api/v1/users/{user}/scans",json={"image_reference":"safe"}).json()["scan_id"]
 assert api.get(f"/api/v1/scans/{scan}?user_id={other}").status_code==404
 assert api.post(f"/api/v1/users/{user}/scans",json={"image_reference":"../unsafe"}).status_code==400
