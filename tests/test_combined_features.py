from datetime import datetime, timedelta

import numpy as np
import pytest

from spectraderm.features.combined_features import CombinedFeatureResult, combine_features
from spectraderm.features.rgb_features import RGBFeatureResult
from spectraderm.features.spectral_features import SpectralFeatureResult


def rgb(value=1.0, extras=None):
    features = {"color_mean_r": value, "gradient_mean": 2.0}
    if extras:
        features.update(extras)
    return RGBFeatureResult(features, {}, 4, 0.5, (2, 2, 3), [])


def spectral(value=2.0, extras=None):
    features = {"ratio_540_650": value, "regional_spectral_mean": 3.0}
    if extras:
        features.update(extras)
    return SpectralFeatureResult(
        features, {}, np.arange(31, dtype=float) + value, np.arange(400, 701, 10),
        4, 0.5, (2, 2, 31), [],
    )


def test_valid_combination_namespaces_and_preserves_values():
    result = combine_features(rgb(), spectral())
    assert isinstance(result, CombinedFeatureResult)
    assert result.current_features["rgb.color_mean_r"] == 1.0
    assert result.current_features["spectral.ratio_540_650"] == 2.0
    assert result.current_features["spectral.signature_400"] == 2.0
    assert result.current_features["spectral.signature_700"] == 32.0


@pytest.mark.parametrize("bad_rgb,bad_spectral", [(None, spectral()), (rgb(), None), ({}, spectral()), (rgb(), {})])
def test_missing_or_wrong_source_results_rejected(bad_rgb, bad_spectral):
    with pytest.raises(TypeError):
        combine_features(bad_rgb, bad_spectral)


def test_nonfinite_and_nonnumeric_source_values_excluded_from_ml_vector():
    result = combine_features(rgb(extras={"bad": np.inf, "text": "x"}), spectral())
    assert "rgb.bad" not in result.current_features
    assert "rgb.text" not in result.current_features
    assert np.isfinite(result.ml_vector).all()
    assert result.warnings


def test_metadata_is_separate_from_ml_vector():
    result = combine_features(rgb(), spectral(), metadata={"observation_id": "obs-a", "subject_key": "anon-7"})
    assert result.metadata.observation_id == "obs-a"
    assert result.metadata.subject_key == "anon-7"
    assert not any("obs-a" in name or "subject" in name for name in result.feature_names)


def test_current_order_is_stable_and_rgb_then_spectral():
    first = combine_features(rgb(extras={"z": 3, "a": 4}), spectral(extras={"z": 5, "a": 6}))
    second = combine_features(rgb(extras={"a": 4, "z": 3}), spectral(extras={"a": 6, "z": 5}))
    current_names = [name for name in first.feature_names if not name.startswith("temporal.")]
    assert first.feature_names == second.feature_names
    assert current_names == sorted(current_names)
    assert current_names[0].startswith("rgb.")


def test_baseline_has_honest_missing_history_representation():
    result = combine_features(rgb(), spectral())
    assert result.metadata.temporal_status == "baseline"
    assert result.metadata.history_available is False
    assert np.isnan(result.temporal_features["temporal.rgb.color_mean_r.delta"])
    assert result.temporal_features["temporal.rgb.color_mean_r.available"] == 0.0
    assert result.temporal_features["temporal.history_available"] == 0.0
    assert np.isfinite(result.ml_vector).all()


def test_follow_up_temporal_formulas_and_elapsed_days():
    baseline = combine_features(rgb(2.0), spectral(4.0))
    start = datetime(2024, 1, 1)
    result = combine_features(rgb(5.0), spectral(10.0), baseline, start + timedelta(days=2), start)
    key = "temporal.rgb.color_mean_r"
    assert result.metadata.temporal_status == "follow_up"
    assert result.metadata.history_available is True
    assert result.metadata.elapsed_days == 2.0
    assert result.temporal_features[f"{key}.delta"] == 3.0
    assert result.temporal_features[f"{key}.abs_delta"] == 3.0
    assert result.temporal_features[f"{key}.relative_change"] == pytest.approx(1.5)
    assert result.temporal_features[f"{key}.rate_per_day"] == pytest.approx(1.5)
    assert result.temporal_features[f"{key}.available"] == 1.0


def test_zero_baseline_relative_change_is_nan_with_warning():
    baseline = combine_features(rgb(0.0), spectral())
    result = combine_features(rgb(1.0), spectral(), baseline)
    assert np.isnan(result.temporal_features["temporal.rgb.color_mean_r.relative_change"])
    assert any("relative_change" in warning for warning in result.warnings)


@pytest.mark.parametrize("offset", [0, -1])
def test_zero_or_negative_elapsed_days_make_rate_nan(offset):
    baseline = combine_features(rgb(), spectral())
    now = datetime(2024, 1, 2)
    result = combine_features(rgb(2), spectral(), baseline, now + timedelta(days=offset), now)
    assert np.isnan(result.temporal_features["temporal.rgb.color_mean_r.rate_per_day"])
    assert any("elapsed_days" in warning for warning in result.warnings)


def test_one_timestamp_does_not_fabricate_rate():
    baseline = combine_features(rgb(), spectral())
    result = combine_features(rgb(2), spectral(), baseline, datetime(2024, 1, 2), None)
    assert np.isnan(result.temporal_features["temporal.rgb.color_mean_r.rate_per_day"])


def test_missing_schema_is_warned_and_not_compared():
    baseline = combine_features(rgb(extras={"old_only": 1}), spectral())
    result = combine_features(rgb(), spectral(), baseline)
    assert any("unmatched" in warning for warning in result.warnings)
    assert "temporal.rgb.old_only.delta" not in result.temporal_features


def test_tuple_baseline_is_supported():
    result = combine_features(rgb(2), spectral(3), (rgb(1), spectral(2)))
    assert result.temporal_features["temporal.rgb.color_mean_r.delta"] == 1.0


def test_feature_names_align_vector_and_group_ordering():
    result = combine_features(rgb(), spectral())
    assert len(result.feature_names) == len(result.ml_vector)
    delta_start = result.feature_names.index("temporal.rgb.color_mean_r.delta")
    abs_start = result.feature_names.index("temporal.rgb.color_mean_r.abs_delta")
    relative_start = result.feature_names.index("temporal.rgb.color_mean_r.relative_change")
    rate_start = result.feature_names.index("temporal.rgb.color_mean_r.rate_per_day")
    available_start = result.feature_names.index("temporal.history_available")
    assert delta_start < abs_start < relative_start < rate_start < available_start
    assert result.ml_vector.dtype == np.float32


def test_deterministic_output_and_no_metadata_comparison():
    baseline = combine_features(rgb(), spectral(), metadata={"observation_id": "base"})
    first = combine_features(rgb(2), spectral(3), baseline, metadata={"observation_id": "now"})
    second = combine_features(rgb(2), spectral(3), baseline, metadata={"observation_id": "other"})
    assert first.feature_names == second.feature_names
    assert np.array_equal(first.ml_vector, second.ml_vector)
    assert not any("observation" in name for name in first.temporal_features)


def test_invalid_metadata_and_timestamps_rejected():
    with pytest.raises(TypeError):
        combine_features(rgb(), spectral(), metadata="bad")
    with pytest.raises(TypeError):
        combine_features(rgb(), spectral(), current_timestamp="bad")
    with pytest.raises(ValueError):
        combine_features(rgb(), spectral(), current_timestamp=datetime.now() + timedelta(days=1))


@pytest.mark.parametrize("current_value,baseline_value,expected_delta", [
    (1.0, 1.0, 0.0), (2.0, 1.0, 1.0), (-1.0, 1.0, -2.0),
    (0.5, -0.5, 1.0), (10.0, 2.0, 8.0), (3.0, 5.0, -2.0),
])
def test_temporal_delta_is_exact_for_matching_scalar_features(current_value, baseline_value, expected_delta):
    baseline = combine_features(rgb(baseline_value), spectral())
    result = combine_features(rgb(current_value), spectral(), baseline)
    assert result.temporal_features["temporal.rgb.color_mean_r.delta"] == expected_delta
