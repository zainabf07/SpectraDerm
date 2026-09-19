from fastapi.testclient import TestClient
from spectraderm.api.app import create_app
from spectraderm.api.config import APISettings
from spectraderm.api.dependencies import ServiceContainer
class FakeActions:
 def products(self, analysis): return None if analysis["safety_result"]["professional_assessment_recommended"] else {"status":"available","recommendations":[{"category_id":"gentle_cleanser"}]}
 def referrals(self, analysis, location, radius): return {"status":"available","options":[{"name":"Synthetic Clinic","source":"synthetic"}]} if analysis["safety_result"]["professional_assessment_recommended"] else None
def setup(tmp_path, referral):
 c=ServiceContainer(APISettings(storage_root=tmp_path)); c.actions=FakeActions(); api=TestClient(create_app(APISettings(storage_root=tmp_path),c)); u=api.post("/api/v1/users",json={}).json()["user_id"]; s=api.post(f"/api/v1/users/{u}/scans",json={"image_reference":"safe"}).json()["scan_id"]; c.analysis_results[s]={"safety_result":{"professional_assessment_recommended":referral}}; return api,u,s
def test_product_permitted_and_referral_blocked_when_safety_false(tmp_path):
 api,u,s=setup(tmp_path,False); assert api.get(f"/api/v1/scans/{s}/products?user_id={u}").json()["items"][0]["category_id"]=="gentle_cleanser"
 assert api.post(f"/api/v1/scans/{s}/referrals?user_id={u}",json={"city":"Synthetic"}).json()["status"]=="not_applicable"
def test_referral_permitted_and_product_blocked_when_safety_true(tmp_path):
 api,u,s=setup(tmp_path,True); assert api.get(f"/api/v1/scans/{s}/products?user_id={u}").json()["status"]=="not_applicable"
 assert api.post(f"/api/v1/scans/{s}/referrals?user_id={u}",json={"city":"Synthetic"}).json()["items"][0]["name"]=="Synthetic Clinic"
def test_action_without_analysis_is_invalid_state(tmp_path):
 c=ServiceContainer(APISettings(storage_root=tmp_path)); api=TestClient(create_app(APISettings(storage_root=tmp_path),c)); u=api.post("/api/v1/users",json={}).json()["user_id"]; s=api.post(f"/api/v1/users/{u}/scans",json={"image_reference":"safe"}).json()["scan_id"]
 assert api.get(f"/api/v1/scans/{s}/products?user_id={u}").status_code==409
def test_provider_failure_is_safe(tmp_path):
 api,u,s=setup(tmp_path,True)
 class Broken:
  def products(self, analysis): return None
  def referrals(self, analysis, location, radius): raise RuntimeError("secret")
 api.app.state.services.actions=Broken()
 response=api.post(f"/api/v1/scans/{s}/referrals?user_id={u}",json={"city":"Synthetic"})
 assert response.status_code==503 and "secret" not in response.text
