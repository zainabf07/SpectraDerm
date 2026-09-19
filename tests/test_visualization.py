import numpy as np
import pytest

from spectraderm.features.combined_features import CombinedFeatureResult, FeatureMetadata
from spectraderm.monitoring.anomaly import analyze_change
from spectraderm.monitoring.baseline import build_personal_baseline
from spectraderm.monitoring.longitudinal import compare_longitudinal
from spectraderm.monitoring.visualization import ChangeVisualization, build_change_visualization


def current(features):
    return CombinedFeatureResult(
        current_features=features, temporal_features={}, combined_features=dict(features),
        ml_vector=np.asarray(list(features.values()), dtype=float), feature_names=list(features),
        metadata=FeatureMetadata("current-1", None, "subject-1", True, "follow_up", None, None, True, 1),
        warnings=[],
    )


def inputs(current_features=None):
    history = [
        {"rgb.mean": 0.0, "spectral.signature_540": 10.0},
        {"rgb.mean": 2.0, "spectral.signature_540": 12.0},
        {"rgb.mean": 4.0, "spectral.signature_540": 14.0},
        {"rgb.mean": 6.0, "spectral.signature_540": 16.0},
    ]
    baseline = build_personal_baseline(history)
    scan = current(current_features or {"rgb.mean": 3.0, "spectral.signature_540": 13.0})
    return baseline, compare_longitudinal(baseline, scan), analyze_change(scan, history)


def test_valid_r_s_q_inputs_build_labeled_visualization():
    baseline, comparison, anomaly = inputs()
    result = build_change_visualization(baseline, comparison, anomaly)
    assert isinstance(result, ChangeVisualization)
    assert result.labels["baseline"] == "Personal Baseline"
    assert result.labels["current"] == "Current Scan"
    assert result.labels["feature_change"] == "Feature Change"
    assert result.labels["score"] == "Model-Derived Change Score"
    assert result.score_panel["change_score"] == anomaly.change_score
    assert result.metadata["baseline_observation_count"] == 4


def test_unchanged_data_has_unchanged_rows_and_zero_deltas():
    baseline, comparison, anomaly = inputs({"rgb.mean": 3.0, "spectral.signature_540": 13.0})
    result = build_change_visualization(baseline, comparison, anomaly)
    assert all(row.direction == "unchanged" for row in result.feature_rows)
    assert all(row.delta == 0.0 for row in result.feature_rows)


def test_increased_and_decreased_values_are_labeled():
    baseline, comparison, anomaly = inputs({"rgb.mean": 5.0, "spectral.signature_540": 11.0})
    result = build_change_visualization(baseline, comparison, anomaly)
    directions = {row.feature_name: row.direction for row in result.feature_rows}
    assert directions == {"rgb.mean": "increased", "spectral.signature_540": "decreased"}


def test_missing_or_unavailable_features_are_exposed():
    baseline = build_personal_baseline([{"rgb.available": 1.0, "rgb.unavailable": np.nan}])
    scan = current({"rgb.available": 2.0, "spectral.current_only": 3.0})
    comparison = compare_longitudinal(baseline, scan)
    anomaly = analyze_change(scan, [{"rgb.available": 1.0}, {"rgb.available": 2.0}, {"rgb.available": 3.0}, {"rgb.available": 4.0}])
    result = build_change_visualization(baseline, comparison, anomaly)
    rows = {row.feature_name: row for row in result.feature_rows}
    assert rows["rgb.unavailable"].direction == "unavailable"
    assert rows["spectral.current_only"].status == "baseline_missing"


def test_repeated_output_is_deterministic():
    values = inputs()
    assert build_change_visualization(*values) == build_change_visualization(*values)


@pytest.mark.parametrize("baseline,comparison,anomaly", [(None, None, None), ("bad", "bad", "bad")])
def test_invalid_inputs_are_rejected(baseline, comparison, anomaly):
    with pytest.raises(TypeError):
        build_change_visualization(baseline, comparison, anomaly)
