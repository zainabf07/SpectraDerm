from fastapi.testclient import TestClient
from spectraderm.api.app import create_app
from spectraderm.api.config import APISettings
def test_report_uses_aj_and_preserves_safe_sections(tmp_path):
 api=TestClient(create_app(APISettings(storage_root=tmp_path))); u=api.post("/api/v1/users",json={}).json()["user_id"]; s=api.post(f"/api/v1/users/{u}/scans",json={"image_reference":"safe"}).json()["scan_id"]
 result=api.get(f"/api/v1/scans/{s}/report?user_id={u}").json()
 assert len(result["sections"])==11 and result["sections"][3]["items"][0]["value"]=="AI-estimated spectral representation"
def test_missing_report_scan_is_not_found(tmp_path): assert TestClient(create_app(APISettings(storage_root=tmp_path))).get("/api/v1/scans/no/report?user_id=no").status_code==404
def test_report_receives_actual_adapter_spectral_availability(tmp_path):
 api=TestClient(create_app(APISettings(storage_root=tmp_path))); u=api.post("/api/v1/users",json={}).json()["user_id"]; s=api.post(f"/api/v1/users/{u}/scans",json={"image_reference":"safe"}).json()["scan_id"]
 api.app.state.services.analysis_results[s]={"metadata":{"pipeline":{"spectral_reconstruction_available":True,"spectral_reconstruction_unavailable_reason":None}}}
 spectral=api.get(f"/api/v1/scans/{s}/report?user_id={u}").json()["sections"][3]
 assert spectral["status"]=="available" and any(item["label"]=="reconstruction_method" for item in spectral["items"])
