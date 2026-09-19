from spectraderm.agents.monitoring_agent import HistoricalScanRecord, MonitoringAgent, MonitoringAgentInput


def record(scan_id, timestamp, score, status="supplied"):
    return HistoricalScanRecord(scan_id, timestamp, score, status, f"summary-{scan_id}")


def run(records=(), change=None, current_scan_id=None, **kwargs):
    return MonitoringAgent().interpret(MonitoringAgentInput(
        historical_scan_records=tuple(records), change_anomaly_result=change,
        current_scan_id=current_scan_id, **kwargs
    ))


def test_insufficient_history_is_explicit_for_fewer_than_two_valid_scans():
    output = run([record("s1", "2026-01-01", 10)], {"change_score": 10, "category": "Stable"})
    assert output.trend == "insufficient_history"
    assert output.number_of_valid_scans == 1
    assert any("cannot yet be established" in item for item in output.limitations)


def test_two_scans_with_stable_scores_and_two_scans_showing_change():
    stable = run([record("s1", "2026-01-01", 10), record("s2", "2026-01-02", 11)])
    changed = run([record("s1", "2026-01-01", 10), record("s2", "2026-01-02", 20)])
    assert stable.trend == "stable"
    assert changed.trend == "changed"


def test_multiple_successive_scores_produce_increasing_change():
    output = run([record("s1", "2026-01-01", 10), record("s2", "2026-01-02", 15), record("s3", "2026-01-03", 20)])
    assert output.trend == "increasing_change"
    assert "model-derived" in output.safety_message


def test_non_monotonic_scores_are_changed_not_increasing():
    output = run([record("s1", "2026-01-01", 10), record("s2", "2026-01-02", 20), record("s3", "2026-01-03", 15)])
    assert output.trend == "changed"


def test_timestamps_sort_records_deterministically_and_preserve_content():
    late = record("late", "2026-03-01", 30)
    early = record("early", "2026-01-01", 10)
    output = run([late, early], current_scan_id="late")
    assert output.historical_records == (early, late)
    assert output.previous_change_score == 10


def test_missing_scores_and_optional_fields_are_not_fabricated():
    output = run([record("s1", "2026-01-01", None), record("s2", "2026-01-02", "bad")])
    assert output.number_of_valid_scans == 0
    assert output.current_change_score is None
    assert output.previous_change_score is None
    assert output.evidence_inputs["baseline_reference"] is None


def test_supplied_q_and_s_outputs_are_preserved_without_modification():
    q_output = {"change_score": 30.0, "category": "Monitor"}
    s_output = {"delta": {"spectral.x": 0.2}}
    output = run([record("s1", "2026-01-01", 20), record("s2", "2026-01-02", 30)], q_output,
                 current_comparison=s_output)
    assert output.current_status == "changed"
    assert output.evidence_inputs["change_anomaly_result"] is q_output
    assert output.evidence_inputs["current_comparison"] is s_output


def test_repeated_execution_is_deterministic_and_has_no_disease_probability():
    source = [record("s1", "2026-01-01", 10), record("s2", "2026-01-02", 20)]
    first = run(source, {"change_score": 20, "category": "Monitor"})
    second = run(source, {"change_score": 20, "category": "Monitor"})
    assert first == second
    assert "disease probability" in first.safety_message
    assert "probability" not in first.summary.lower()
