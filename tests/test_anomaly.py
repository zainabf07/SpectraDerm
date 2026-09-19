import math

import numpy as np
import pytest

from spectraderm.monitoring.anomaly import ChangeAnomalyAnalyzer, ChangeAnomalyConfig, analyze_change


def observation(rgb=10.0, spectral=100.0, **extra):
    values = {"rgb.texture": rgb, "spectral.signature_540": spectral}
    values.update(extra)
    return values


@pytest.fixture
def history():
    return [observation(8, 80), observation(10, 100), observation(12, 120), observation(14, 140)]


def test_identical_to_reference_median_is_stable_with_zero_score(history):
    result = analyze_change(observation(11, 110), history)
    assert result.change_score == pytest.approx(0.0)
    assert result.category == "Stable"


def test_small_and_large_changes_have_ordered_bounded_scores(history):
    small = analyze_change(observation(12, 120), history)
    large = analyze_change(observation(30, 300), history)
    assert 0 < small.change_score < large.change_score <= 100
    assert small.category == "Stable"


def test_iqr_scaling_uses_history_only_and_is_correct():
    # Median=3, IQR=3 for each group; each distance is |6-3| / 3 = 1.
    reference = [observation(0, 0), observation(2, 2), observation(4, 4), observation(6, 6)]
    result = analyze_change(observation(6, 6), reference)
    assert result.rgb_change == pytest.approx(1.0)
    assert result.spectral_change == pytest.approx(1.0)
    assert result.change_score == pytest.approx(100 * (1 - math.exp(-1)))


def test_different_numeric_ranges_are_comparable_after_iqr_scaling():
    reference = [observation(0, 0), observation(10, 1000), observation(20, 2000), observation(30, 3000)]
    result = analyze_change(observation(25, 2500), reference)
    assert result.rgb_change == pytest.approx(result.spectral_change)


def test_rgb_and_spectral_groups_have_equal_weight_despite_feature_count():
    reference = []
    for value in (0, 2, 4, 6):
        reference.append({"rgb.one": value, **{f"spectral.many_{i}": value for i in range(10)}})
    current = {"rgb.one": 6, **{f"spectral.many_{i}": 3 for i in range(10)}}
    result = analyze_change(current, reference)
    # RGB distance=1; spectral mean=0; equal group mean is 0.5, not 1/11.
    assert result.change_score == pytest.approx(100 * (1 - math.exp(-0.5)))


def test_nonfinite_current_and_reference_values_are_excluded(history):
    current = observation(11, 110, **{"rgb.bad": np.nan})
    refs = [{**item, "rgb.bad": 1.0} for item in history]
    result = analyze_change(current, refs)
    assert result.features_excluded_nonfinite == 1
    assert result.features_compared == 2
    refs[0]["rgb.bad"] = np.inf
    result = analyze_change(observation(11, 110, **{"rgb.bad": 2.0}), refs)
    assert result.features_excluded_nonfinite == 1


def test_zero_iqr_features_are_excluded_not_exploded():
    reference = [{"rgb.fixed": 2.0, "spectral.variable": value} for value in (0, 2, 4, 6)]
    result = analyze_change({"rgb.fixed": 999.0, "spectral.variable": 3.0}, reference)
    assert result.features_excluded_zero_variance == 1
    assert result.rgb_change is None
    assert result.spectral_change == pytest.approx(0.0)
    assert result.change_score == pytest.approx(0.0)
    assert any("Reduced group coverage" in warning for warning in result.warnings)


def test_insufficient_history_is_safe_and_configurable():
    result = analyze_change(observation(), [observation(), observation(), observation()])
    assert result.change_score is None
    assert result.category is None
    assert not result.sufficient_reference_history
    assert "Insufficient reference history" in result.interpretation
    configured = analyze_change(observation(), [observation(), observation()], ChangeAnomalyConfig(2))
    assert configured.sufficient_reference_history


@pytest.mark.parametrize("score,category", [(0.0, "Stable"), (39.0, "Stable"), (40.0, "Monitor"), (69.0, "Monitor"), (70.0, "Higher Change"), (100.0, "Higher Change")])
def test_categories_follow_engineering_thresholds(score, category):
    assert ChangeAnomalyAnalyzer()._category(score) == category


def test_interpretation_has_no_disease_or_diagnosis_language(history):
    result = analyze_change(observation(30, 300), history)
    text = " ".join([result.interpretation, *result.warnings]).lower()
    assert "disease" not in text
    assert "diagnos" not in text
    assert "risk" not in text


def test_repeated_identical_inputs_are_deterministic(history):
    first = analyze_change(observation(15, 150), history)
    second = analyze_change(observation(15, 150), history)
    assert first == second

