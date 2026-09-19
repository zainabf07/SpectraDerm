import numpy as np
import pytest

from spectraderm.features.combined_features import CombinedFeatureResult, FeatureMetadata
from spectraderm.monitoring.baseline import build_personal_baseline
from spectraderm.monitoring.longitudinal import LongitudinalComparison, compare_longitudinal


def current(features, observation_id="current-1"):
    return CombinedFeatureResult(
        current_features=features,
        temporal_features={},
        combined_features=dict(features),
        ml_vector=np.asarray(list(features.values()), dtype=float),
        feature_names=list(features),
        metadata=FeatureMetadata(observation_id, None, "subject-1", True, "follow_up", None, None, True, 1),
        warnings=[],
    )


def baseline(**values):
    return build_personal_baseline([values])


def test_identical_baseline_and_current_have_zero_deltas():
    result = compare_longitudinal(baseline(**{"rgb.mean": 2.0, "spectral.signature_540": 4.0}), current({"rgb.mean": 2.0, "spectral.signature_540": 4.0}))
    assert isinstance(result, LongitudinalComparison)
    assert result.delta["rgb.mean"] == 0.0
    assert result.absolute_delta["spectral.signature_540"] == 0.0
    assert result.summary["unchanged_features"] == 2


def test_increased_and_decreased_features_are_reported():
    result = compare_longitudinal(baseline(**{"rgb.mean": 2.0, "spectral.signature_540": 4.0}), current({"rgb.mean": 3.0, "spectral.signature_540": 1.0}))
    assert result.delta["rgb.mean"] == 1.0
    assert result.delta["spectral.signature_540"] == -3.0
    assert result.summary["increased_features"] == 1
    assert result.summary["decreased_features"] == 1


def test_relative_change_is_correct():
    result = compare_longitudinal(baseline(**{"rgb.mean": -4.0}), current({"rgb.mean": -2.0}))
    assert result.relative_change["rgb.mean"] == pytest.approx(0.5)


def test_zero_baseline_keeps_relative_change_unavailable():
    result = compare_longitudinal(baseline(**{"rgb.mean": 0.0}), current({"rgb.mean": 2.0}))
    assert result.delta["rgb.mean"] == 2.0
    assert result.relative_change["rgb.mean"] is None
    assert result.feature_status["rgb.mean"] == "comparable_relative_change_unavailable_zero_baseline"


def test_missing_and_nonfinite_features_are_explicitly_unavailable():
    reference = build_personal_baseline([{"rgb.present": 1.0, "rgb.unavailable": np.nan, "spectral.only_baseline": 2.0}])
    result = compare_longitudinal(reference, current({"rgb.present": np.nan, "spectral.only_current": 3.0}))
    assert result.feature_status["rgb.present"] == "current_nonfinite_or_nonnumeric"
    assert result.feature_status["rgb.unavailable"] == "baseline_unavailable"
    assert result.feature_status["spectral.only_baseline"] == "current_missing"
    assert result.feature_status["spectral.only_current"] == "baseline_missing"


def test_mismatched_features_and_namespaces_are_not_silently_compared():
    result = compare_longitudinal(baseline(**{"rgb.same_label": 1.0}), current({"spectral.same_label": 1.0}))
    assert result.feature_status == {"rgb.same_label": "current_missing", "spectral.same_label": "baseline_missing"}
    assert result.summary["comparable_features"] == 0


def test_feature_names_are_preserved_and_metadata_is_exposed():
    result = compare_longitudinal(baseline(**{"rgb.texture.mean": 1.0}), current({"rgb.texture.mean": 2.0}, "obs-2"))
    assert list(result.delta) == ["rgb.texture.mean"]
    assert result.metadata["baseline_observation_count"] == 1
    assert result.metadata["current_observation_id"] == "obs-2"


def test_repeated_comparison_is_deterministic():
    reference = baseline(**{"rgb.mean": 1.0})
    observation = current({"rgb.mean": 2.0})
    assert compare_longitudinal(reference, observation) == compare_longitudinal(reference, observation)


@pytest.mark.parametrize("bad_baseline,bad_current", [(None, current({})), (baseline(), None)])
def test_actual_module_r_and_n_types_are_required(bad_baseline, bad_current):
    with pytest.raises(TypeError):
        compare_longitudinal(bad_baseline, bad_current)
