from pathlib import Path
from shutil import copyfile

from fastapi.testclient import TestClient

from spectraderm.api.app import create_app
from spectraderm.api.config import APISettings


FIXTURE_IMAGE = Path(__file__).resolve().parents[1] / "data" / "external" / "hyperskin_sample" / "p001_neutral_front.jpg"
MSTPP_CHECKPOINT = Path(__file__).resolve().parents[1] / "models" / "mstpp_hyperskin_vis_best_10pairs.pth"


def _api_with_managed_fixture(tmp_path):
    artifact = tmp_path / "images" / "fixture.jpg"
    artifact.parent.mkdir()
    copyfile(FIXTURE_IMAGE, artifact)
    api = TestClient(create_app(APISettings(storage_root=tmp_path)))
    user_id = api.post("/api/v1/users", json={}).json()["user_id"]
    scan_id = api.post(
        f"/api/v1/users/{user_id}/scans", json={"image_reference": "images/fixture.jpg"}
    ).json()["scan_id"]
    return api, user_id, scan_id


def test_real_adapter_runs_managed_fixture_through_orchestrator_and_aj(tmp_path):
    api, user_id, scan_id = _api_with_managed_fixture(tmp_path)

    response = api.post(f"/api/v1/scans/{scan_id}/analyze?user_id={user_id}", json={"input": {}})

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["metadata"]["pipeline"]["image_reference"] == "images/fixture.jpg"
    assert result["metadata"]["pipeline"]["rgb_feature_count"] > 0
    assert result["metadata"]["pipeline"]["spectral_reconstruction_available"] is False
    assert result["vision_result"]["image_quality_summary"]["available"] is True
    assert result["errors"] == []
    assert result["evidence_result"]["evidence_count"] > 0
    assert result["evidence_result"]["grounding_status"] == "evidence_found"
    assert result["safety_result"]["professional_assessment_recommended"] is False
    assert result["recommended_path"] == "product"

    report = api.get(f"/api/v1/scans/{scan_id}/report?user_id={user_id}")
    assert report.status_code == 200
    assert len(report.json()["sections"]) == 11


def test_real_adapter_rejects_a_filename_without_a_managed_artifact(tmp_path):
    api = TestClient(create_app(APISettings(storage_root=tmp_path)))
    user_id = api.post("/api/v1/users", json={}).json()["user_id"]
    scan_id = api.post(
        f"/api/v1/users/{user_id}/scans", json={"image_reference": "selected-in-browser.jpg"}
    ).json()["scan_id"]

    response = api.post(f"/api/v1/scans/{scan_id}/analyze?user_id={user_id}", json={"input": {}})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "IMAGE_ARTIFACT_UNAVAILABLE"


def test_real_adapter_exposes_only_derived_mstpp_artifacts_for_a_managed_image(tmp_path):
    artifact = tmp_path / "images" / "fixture.jpg"
    artifact.parent.mkdir()
    copyfile(FIXTURE_IMAGE, artifact)
    api = TestClient(create_app(APISettings(
        storage_root=tmp_path,
        mstpp_checkpoint_path=MSTPP_CHECKPOINT,
        mstpp_device="cpu",
    )))
    user_id = api.post("/api/v1/users", json={}).json()["user_id"]
    scan_id = api.post(
        f"/api/v1/users/{user_id}/scans", json={"image_reference": "images/fixture.jpg"}
    ).json()["scan_id"]

    response = api.post(f"/api/v1/scans/{scan_id}/analyze?user_id={user_id}", json={"input": {}})

    assert response.status_code == 200
    pipeline = response.json()["result"]["metadata"]["pipeline"]
    visualization = pipeline["spectral_visualization"]
    assert pipeline["spectral_reconstruction_available"] is True
    assert pipeline["model_input_shape"] == [256, 256, 3]
    assert visualization["reconstructed_band_count"] == 31
    assert visualization["wavelength_range_nm"] == [400, 700]
    assert visualization["false_color_image"].startswith("data:image/png;base64,")
    assert "spectrum" not in pipeline
