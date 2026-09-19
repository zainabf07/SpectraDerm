import base64
from pathlib import Path

import cv2
import numpy as np

from spectraderm.api.analysis_adapter import build_spectral_visualization
from spectraderm.spectral.visualization import extract_region_spectrum, spectral_to_false_color


REAL_RECONSTRUCTION = Path(__file__).resolve().parents[1] / "data" / "interim" / "p039_vis_prediction.npy"


def _decode_data_url(value: str) -> np.ndarray:
    encoded = value.split(",", 1)[1]
    return cv2.imdecode(np.frombuffer(base64.b64decode(encoded), dtype=np.uint8), cv2.IMREAD_UNCHANGED)


def test_visualization_artifacts_are_derived_from_real_reconstruction_output():
    # This preserved MST++ prediction is stored as model-output CHW; Module K
    # consumes the reconstruction interface's HWC representation.
    cube = np.moveaxis(np.load(REAL_RECONSTRUCTION, allow_pickle=False).astype(np.float32), 0, -1)
    roi = np.zeros(cube.shape[:2], dtype=bool)
    roi[: cube.shape[0] // 2, : cube.shape[1] // 2] = True

    output = build_spectral_visualization(cube, roi)

    expected_false_color = cv2.cvtColor(
        np.clip(spectral_to_false_color(cube) * 255.0, 0, 255).round().astype(np.uint8),
        cv2.COLOR_RGB2BGR,
    )
    assert output["available"] is True
    assert output["wavelength_range_nm"] == (400, 700)
    assert output["reconstructed_band_count"] == 31
    assert np.array_equal(_decode_data_url(output["false_color_image"]), expected_false_color)
    assert output["roi_spectrum"]["values"] == [float(value) for value in extract_region_spectrum(cube, roi)]
