"""Shared pytest configuration.

Importing ``spectraderm.api.app`` loads the project ``.env`` (it builds a
module-level ``app``). Without this fixture, any real API keys in that file
would make the test suite call OpenAI / Google Places over the network.
"""
import pytest


@pytest.fixture(autouse=True)
def _no_external_service_keys(monkeypatch):
    for name in ("OPENAI_API_KEY", "GOOGLE_MAPS_API_KEY"):
        monkeypatch.delenv(name, raising=False)
