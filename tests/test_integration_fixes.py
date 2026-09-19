"""Regression tests for cross-module integration fixes."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from shutil import copyfile

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from spectraderm.agents.product_agent import ProductAgent, ProductAgentInput
from spectraderm.agents.safety_agent import SafetyAgent, SafetyAgentInput
from spectraderm.agents.vision_agent import VisionAgent, VisionAgentInput
from spectraderm.api.app import create_app
from spectraderm.api.config import APISettings
from spectraderm.rag.rag_pipeline import RetrievedEvidence, SourceMetadata
from spectraderm.users.user_management import FileUserRepository, UserManagement


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_IMAGE = ROOT / "data" / "external" / "hyperskin_sample" / "p001_neutral_front.jpg"
MSTPP_CHECKPOINT = ROOT / "models" / "mstpp_hyperskin_vis_best_10pairs.pth"


def test_users_survive_a_restart_of_the_repository(tmp_path):
    record = UserManagement(FileUserRepository(tmp_path)).create_user(True, False)
    reloaded = UserManagement(FileUserRepository(tmp_path)).get_user(record.user_id)
    assert reloaded == record


def test_api_users_and_scans_survive_an_app_restart(tmp_path):
    api = TestClient(create_app(APISettings(storage_root=tmp_path)))
    user_id = api.post("/api/v1/users", json={}).json()["user_id"]
    scan_id = api.post(f"/api/v1/users/{user_id}/scans", json={"image_reference": "images/x.jpg"}).json()["scan_id"]
    restarted = TestClient(create_app(APISettings(storage_root=tmp_path)))
    assert restarted.get(f"/api/v1/users/{user_id}").json()["scan_ids"] == [scan_id]
    assert [item["scan_id"] for item in restarted.get(f"/api/v1/users/{user_id}/history").json()["timeline"]] == [scan_id]


def test_relative_storage_root_resolves_against_the_project(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SPECTRADERM_STORAGE_ROOT", "custom-storage")
    assert APISettings.from_environment().storage_root == (ROOT / "custom-storage").resolve()


@pytest.mark.parametrize(("status", "insufficient"), [("GOOD", False), ("REVIEW", False), ("REJECT", True)])
def test_only_rejected_quality_stops_the_comparison(status, insufficient):
    output = VisionAgent().interpret(VisionAgentInput(image_quality_result={"status": status, "passed": status == "GOOD"}))
    assert (output.overall_status == "insufficient_quality") is insufficient


def test_explicit_unknown_pattern_differs_from_missing_pattern():
    safety = {"professional_assessment_recommended": False}
    assert ProductAgent().recommend(ProductAgentInput(detected_pattern="unknown", safety_result=safety)).status == "insufficient_context"
    assert ProductAgent().recommend(ProductAgentInput(safety_result=safety)).status == "recommendations_available"


def _evidence(text):
    source = SourceMetadata("nhs", "Symptoms", "NHS", "https://example.test", "warning_signs")
    return {"retrieved_evidence": (RetrievedEvidence("c1", text, 0.9, source),), "grounding_status": "explanation_unavailable"}


@pytest.mark.parametrize(("monitoring", "expected"), [
    ({"trend": "insufficient_history", "current_status": "unavailable", "previous_change_score": None}, False),
    ({"trend": "insufficient_history", "current_status": "changed", "previous_change_score": 12.0}, False),
    ({"trend": "changed", "current_status": "changed", "previous_change_score": 90.0}, True),
    ({"trend": "increasing_change", "current_status": "changed", "previous_change_score": 30.0}, True),
])
def test_referral_needs_persistent_change_and_professional_evidence(monitoring, expected):
    output = SafetyAgent().evaluate(SafetyAgentInput(
        finding_summary="Model-derived change.", monitoring_result=monitoring,
        evidence_result=_evidence("The source advises contacting a GP if there are concerns about a changing mole."),
    ))
    assert output.professional_assessment_recommended is expected


@pytest.mark.skipif(not MSTPP_CHECKPOINT.is_file(), reason="MST++ checkpoint is not available")
def test_history_scores_persist_and_older_scans_ignore_later_history(tmp_path):
    settings = APISettings(storage_root=tmp_path, mstpp_checkpoint_path=MSTPP_CHECKPOINT, mstpp_device="cpu")
    api = TestClient(create_app(settings))
    user_id = api.post("/api/v1/users", json={}).json()["user_id"]
    base = cv2.imread(str(FIXTURE_IMAGE))
    rng = np.random.default_rng(3)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    scan_ids = []
    for index in range(6):
        image = np.clip(base.astype(float) * (1 + 0.03 * (index % 3 - 1)) + rng.normal(0, 2, base.shape), 0, 255)
        reference = f"images/{user_id}/fixture_{index}.jpg"
        (tmp_path / reference).parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(tmp_path / reference), image.astype(np.uint8))
        scan_ids.append(api.post(f"/api/v1/users/{user_id}/scans", json={
            "image_reference": reference, "timestamp": (start + timedelta(days=index)).isoformat(),
        }).json()["scan_id"])
    results = [api.post(f"/api/v1/scans/{scan_id}/analyze?user_id={user_id}", json={"input": {}}).json()["result"] for scan_id in scan_ids]

    assert results[4]["monitoring_result"]["current_change_score"] is not None
    assert results[5]["monitoring_result"]["previous_change_score"] == pytest.approx(results[4]["monitoring_result"]["current_change_score"])
    # Re-opening the first scan must not use the five later scans as its history.
    reopened = api.post(f"/api/v1/scans/{scan_ids[0]}/analyze?user_id={user_id}", json={"input": {}}).json()["result"]
    assert reopened["monitoring_result"]["evidence_inputs"]["reference_scan_count"] == 0
    assert "baseline_reference" not in str(reopened["evidence_result"]["monitoring_context"])


def test_unconfigured_referral_provider_is_reported_as_provider_error():
    from spectraderm.agents.referral_agent import ReferralAgent, ReferralAgentInput
    from spectraderm.referral.dermatologist_api import DermatologistSearchService, GooglePlacesProvider

    agent = ReferralAgent(DermatologistSearchService(GooglePlacesProvider(api_key=""), "google_places"))
    output = agent.refer(ReferralAgentInput(
        safety_result={"professional_assessment_recommended": True}, location={"city": "Lahore"}, radius_km=10,
    ))
    assert output.status == "provider_error"
