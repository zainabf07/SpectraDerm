import torch

from spectraderm.spectral.cnn_baseline import RGBToSpectralCNN


def test_model_returns_31_bands():
    model = RGBToSpectralCNN(output_bands=31)

    x = torch.rand(2, 3, 64, 64)
    y = model(x)

    assert y.shape == (2, 31, 64, 64)


def test_model_returns_33_bands():
    model = RGBToSpectralCNN(output_bands=33)

    x = torch.rand(1, 3, 32, 32)
    y = model(x)

    assert y.shape == (1, 33, 32, 32)


def test_model_output_is_bounded():
    model = RGBToSpectralCNN(output_bands=31)

    x = torch.rand(1, 3, 32, 32)
    y = model(x)

    assert float(y.min()) >= 0.0
    assert float(y.max()) <= 1.0