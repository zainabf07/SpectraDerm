import numpy as np
import pytest

from spectraderm.features.combined_features import CombinedFeatureResult, FeatureMetadata
from spectraderm.monitoring.baseline import PersonalBaselineResult, build_personal_baseline


def observation(rgb=1.0, spectral=10.0, **extra):
    values = {"rgb.color_mean_r": rgb, "spectral.signature_540": spectral}
    values.update(extra)
    return values


def test_one_observation_preserves_finite_baseline_values_and_count():
    result = build_personal_baseline([observation(2.0, 20.0)])
    assert isinstance(result, PersonalBaselineResult)
    assert result.baseline_features == observation(2.0, 20.0)
    assert result.feature_contributions == {"rgb.color_mean_r": 1, "spectral.signature_540": 1}
    assert result.observation_count == 1


def test_multiple_observations_use_per_feature_median():
    result = build_personal_baseline([observation(1, 10), observation(5, 50), observation(3, 30)])
    assert result.baseline_features["rgb.color_mean_r"] == 3.0
    assert result.baseline_features["spectral.signature_540"] == 30.0


def test_nonfinite_values_are_ignored_without_zero_imputation():
    result = build_personal_baseline([
        observation(1.0, 10.0),
        observation(np.nan, 30.0),
        observation(np.inf, 50.0),
    ])
    assert result.baseline_features["rgb.color_mean_r"] == 1.0
    assert result.feature_contributions["rgb.color_mean_r"] == 1
    assert result.baseline_features["spectral.signature_540"] == 30.0
    assert result.feature_contributions["spectral.signature_540"] == 3


def test_feature_with_no_finite_observations_remains_unavailable():
    result = build_personal_baseline([
        observation(**{"rgb.unavailable": np.nan}),
        observation(**{"rgb.unavailable": -np.inf}),
    ])
    assert "rgb.unavailable" not in result.baseline_features
    assert result.feature_contributions["rgb.unavailable"] == 0
    assert result.unavailable_features == ("rgb.unavailable",)


def test_feature_names_and_namespaces_are_preserved():
    result = build_personal_baseline([
        {"rgb.texture.mean": 1.0, "spectral.signature_500": 2.0},
        {"rgb.texture.mean": 3.0, "spectral.signature_500": 4.0},
    ])
    assert set(result.baseline_features) == {"rgb.texture.mean", "spectral.signature_500"}
    assert result.baseline_features["rgb.texture.mean"] == 2.0


def test_module_n_combined_feature_result_uses_current_features():
    module_n_result = CombinedFeatureResult(
        current_features={"rgb.color_mean_r": 2.0, "spectral.signature_540": 20.0},
        temporal_features={},
        combined_features={"rgb.color_mean_r": 2.0, "spectral.signature_540": 20.0},
        ml_vector=np.asarray([2.0, 20.0], dtype=np.float32),
        feature_names=["rgb.color_mean_r", "spectral.signature_540"],
        metadata=FeatureMetadata(None, None, None, False, "baseline", None, None, True, 1),
        warnings=[],
    )
    result = build_personal_baseline([module_n_result])
    assert result.baseline_features == module_n_result.current_features


@pytest.mark.parametrize("invalid", [None, {}, "not observations", [None], [{"rgb.value": "bad"}]])
def test_invalid_or_incompatible_input_is_rejected(invalid):
    with pytest.raises((TypeError, ValueError)):
        build_personal_baseline(invalid)


def test_repeated_execution_is_deterministic():
    history = [observation(1, 10), observation(3, 30), observation(5, 50)]
    assert build_personal_baseline(history) == build_personal_baseline(history)
