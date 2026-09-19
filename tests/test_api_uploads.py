from pathlib import Path

from fastapi.testclient import TestClient

from spectraderm.api.app import create_app
from spectraderm.api.config import APISettings
from spectraderm.storage.scan_storage import MAX_IMAGE_ARTIFACT_BYTES


FIXTURE_IMAGE = Path(__file__).resolve().parents[1] / "data" / "external" / "hyperskin_sample" / "p001_neutral_front.jpg"


def _api_and_user(tmp_path):
    api = TestClient(create_app(APISettings(storage_root=tmp_path)))
    user_id = api.post("/api/v1/users", json={}).json()["user_id"]
    return api, user_id


def test_upload_creates_an_ag_managed_reference_for_scan_analysis(tmp_path):
    api, user_id = _api_and_user(tmp_path)
    with FIXTURE_IMAGE.open("rb") as image:
        upload = api.post(
            f"/api/v1/users/{user_id}/image-artifacts",
            files={"file": ("browser-name.jpg", image, "image/jpeg")},
        )

    assert upload.status_code == 201
    reference = upload.json()["image_reference"]
    assert reference.startswith(f"images/{user_id}/img_") and reference.endswith(".jpg")
    assert (tmp_path / reference).is_file()

    scan = api.post(f"/api/v1/users/{user_id}/scans", json={"image_reference": reference})
    assert scan.status_code == 201
    analysis = api.post(f"/api/v1/scans/{scan.json()['scan_id']}/analyze?user_id={user_id}", json={"input": {}})
    assert analysis.status_code == 200


def test_upload_rejects_non_images_and_excessive_size(tmp_path):
    api, user_id = _api_and_user(tmp_path)

    invalid = api.post(
        f"/api/v1/users/{user_id}/image-artifacts",
        files={"file": ("not-an-image.jpg", b"not an image", "image/jpeg")},
    )
    assert invalid.status_code == 415 and invalid.json()["error"]["code"] == "UNSUPPORTED_IMAGE"

    oversized = api.post(
        f"/api/v1/users/{user_id}/image-artifacts",
        files={"file": ("large.jpg", b"x" * (MAX_IMAGE_ARTIFACT_BYTES + 1), "image/jpeg")},
    )
    assert oversized.status_code == 413 and oversized.json()["error"]["code"] == "IMAGE_TOO_LARGE"


def test_upload_requires_an_existing_user(tmp_path):
    api = TestClient(create_app(APISettings(storage_root=tmp_path)))
    with FIXTURE_IMAGE.open("rb") as image:
        response = api.post(
            "/api/v1/users/missing/image-artifacts",
            files={"file": ("fixture.jpg", image, "image/jpeg")},
        )
    assert response.status_code == 404 and response.json()["error"]["code"] == "USER_NOT_FOUND"
