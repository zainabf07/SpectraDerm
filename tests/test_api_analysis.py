from fastapi.testclient import TestClient
from spectraderm.api.app import create_app
from spectraderm.api.config import APISettings
from spectraderm.api.dependencies import ServiceContainer
class FakeAnalysis:
 def analyze(self, scan, payload): return {"status":"completed","vision_result":{"finding_summary":"model-derived finding"},"safety_result":{"professional_assessment_recommended":False},"recommended_path":"product"}
class BrokenAnalysis:
 def analyze(self, scan, payload): raise RuntimeError("internal detail")
def setup(tmp_path, analysis):
 c=ServiceContainer(APISettings(storage_root=tmp_path)); c.analysis=analysis; api=TestClient(create_app(APISettings(storage_root=tmp_path),c)); u=api.post("/api/v1/users",json={}).json()["user_id"]; s=api.post(f"/api/v1/users/{u}/scans",json={"image_reference":"safe"}).json()["scan_id"]; return api,u,s
def test_analysis_delegates_and_preserves_safety(tmp_path):
 api,u,s=setup(tmp_path,FakeAnalysis()); response=api.post(f"/api/v1/scans/{s}/analyze?user_id={u}",json={"input":{}})
 assert response.status_code==200 and response.json()["safety"]["professional_assessment_recommended"] is False
def test_analysis_failure_and_missing_scan_are_safe(tmp_path):
 api,u,s=setup(tmp_path,BrokenAnalysis()); assert api.post(f"/api/v1/scans/{s}/analyze?user_id={u}",json={}).status_code==503
 assert api.post(f"/api/v1/scans/no/analyze?user_id={u}",json={}).status_code==404
