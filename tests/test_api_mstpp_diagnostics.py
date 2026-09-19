import logging

import numpy as np

from spectraderm.api.analysis_adapter import AnalysisAdapterConfig, AnalysisOrchestrationAdapter, _mstpp_input_rgb


def test_missing_checkpoint_is_logged_without_exposing_it_in_the_result(tmp_path, caplog):
    adapter = AnalysisOrchestrationAdapter(object(), object(), AnalysisAdapterConfig(tmp_path / "missing.pth"))

    with caplog.at_level(logging.WARNING, logger="spectraderm.api.analysis_adapter"):
        reconstruction, features, reason = adapter._reconstruct(np.zeros((2, 2, 3), dtype=np.uint8), None)

    assert reconstruction is None and features is None
    assert reason == "MST++ reconstruction checkpoint is not configured or unavailable."
    assert "configured checkpoint is unavailable" in caplog.text


def test_mstpp_exception_is_logged_but_the_api_reason_remains_safe(tmp_path, monkeypatch, caplog):
    checkpoint = tmp_path / "checkpoint.pth"
    checkpoint.touch()
    adapter = AnalysisOrchestrationAdapter(object(), object(), AnalysisAdapterConfig(checkpoint))

    def fail(*_args, **_kwargs):
        raise RuntimeError("checkpoint schema mismatch")

    monkeypatch.setattr("spectraderm.api.analysis_adapter.reconstruct_spectral", fail)
    with caplog.at_level(logging.ERROR, logger="spectraderm.api.analysis_adapter"):
        reconstruction, features, reason = adapter._reconstruct(np.zeros((2, 2, 3), dtype=np.uint8), None)

    assert reconstruction is None and features is None
    assert reason == "MST++ reconstruction could not be completed."
    assert "checkpoint schema mismatch" in caplog.text


def test_live_mstpp_input_uses_the_existing_256_pixel_inference_contract():
    browser_sized_rgb = np.full((1024, 768, 3), 127, dtype=np.uint8)

    model_rgb = _mstpp_input_rgb(browser_sized_rgb, 256)

    assert model_rgb.shape == (256, 256, 3)
    assert model_rgb.dtype == np.float32
    assert model_rgb.min() >= 0.0 and model_rgb.max() <= 1.0
