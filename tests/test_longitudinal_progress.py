from datetime import datetime, timedelta, timezone
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from spectraderm.api.app import create_app
from spectraderm.api.config import APISettings
from spectraderm.api.rag_adapter import extractive_explanation
from spectraderm.monitoring.progress import KEY_PARAMETERS, plain_language_finding, summarize_progress
from spectraderm.rag.rag_pipeline import RetrievedEvidence, SourceMetadata

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_IMAGE = ROOT / "data" / "external" / "hyperskin_sample" / "p001_neutral_front.jpg"
MSTPP_CHECKPOINT = ROOT / "models" / "mstpp_hyperskin_vis_best_10pairs.pth"


def features(scale):
    return {name: 1.0 * scale for _, _, name in KEY_PARAMETERS}


def test_scan_one_is_the_baseline_without_change_or_trend():
    result = summarize_progress(features(1.0), [])
    assert result.stage == "baseline" and result.status_label == "Baseline established"
    assert result.change_percent is None and result.change_score is None and result.trend is None


def test_scan_two_shows_the_first_change_but_no_trend():
    result = summarize_progress(features(1.2), [("s1", "2026-01-01", features(1.0), None)])
    assert result.stage == "first_comparison"
    assert result.change_percent == pytest.approx(20.0)
    assert result.change_score is not None and result.direction_vs_previous == "increased"
    assert result.trend is None
    assert all(item.direction == "increased" for item in result.parameters)


@pytest.mark.parametrize(("previous", "current", "trend"), [(1.1, 1.3, "increasing"), (1.3, 1.1, "decreasing"), (1.2, 1.2, "stable")])
def test_scan_three_adds_a_trend(previous, current, trend):
    history = [("s1", "2026-01-01", features(1.0), None)]
    second = summarize_progress(features(previous), history)
    history.append(("s2", "2026-01-02", features(previous), {"change_score": second.change_score, "change_percent": second.change_percent}))
    third = summarize_progress(features(current), history)
    assert third.stage == "trend" and third.trend == trend
    assert [point.scan_number for point in third.history] == [1, 2]


def test_finding_and_source_only_explanation_stay_non_diagnostic():
    progress = summarize_progress(features(1.3), [("s1", "t", features(1.0), None)])
    finding = plain_language_finding(progress)
    assert "30%" in finding and "baseline" in finding
    source = SourceMetadata("nhs", "Moles", "NHS", "https://example.test", "t")
    text = extractive_explanation(finding, (RetrievedEvidence("c", "Changes can have many causes. It does not mean SpectraDerm detects anything.", 1.0, source),))
    assert "[NHS]" in text and "SpectraDerm detects" not in text
    assert "does not identify a specific condition" in text


@pytest.mark.skipif(not MSTPP_CHECKPOINT.is_file(), reason="MST++ checkpoint is not available")
def test_monitoring_report_follows_the_scan_journey(tmp_path):
    settings = APISettings(storage_root=tmp_path, mstpp_checkpoint_path=MSTPP_CHECKPOINT, mstpp_device="cpu")
    api = TestClient(create_app(settings))
    user_id = api.post("/api/v1/users", json={}).json()["user_id"]
    base = cv2.imread(str(FIXTURE_IMAGE))
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    reports = []
    for index in range(3):
        image = base.astype(float)
        if index:
            image[300:600, 350:650, 2] *= 1 + 0.15 * index
        reference = f"images/{user_id}/scan_{index}.jpg"
        (tmp_path / reference).parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(tmp_path / reference), np.clip(image, 0, 255).astype(np.uint8))
        scan_id = api.post(f"/api/v1/users/{user_id}/scans", json={
            "image_reference": reference, "timestamp": (start + timedelta(days=30 * index)).isoformat(),
        }).json()["scan_id"]
        assert api.post(f"/api/v1/scans/{scan_id}/analyze?user_id={user_id}", json={"input": {}}).status_code == 200
        reports.append(api.get(f"/api/v1/scans/{scan_id}/monitoring-report?user_id={user_id}").json())

    first, second, third = reports
    assert first["overall"]["stage"] == "baseline" and first["detected_change"]["available"] is False
    assert second["overall"]["change_percent"] > 0 and second["overall"]["trend"] is None
    assert second["region"]["difference_map"].startswith("data:image/")
    assert third["overall"]["trend"] == "increasing"
    assert [point["scan_number"] for point in third["history"]["points"]] == [1, 2, 3]
    assert third["explanation"]["text"] and third["explanation"]["evidence_count"] > 0
    assert "not a disease probability" in third["overall"]["score_note"]
    timeline = api.get(f"/api/v1/users/{user_id}/history").json()["timeline"]
    assert [item["status_label"] for item in timeline][0] == "Baseline established"
    assert timeline[2]["change_percent"] == third["overall"]["change_percent"]
