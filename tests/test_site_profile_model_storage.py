"""Where the SiteProfile model path comes from: serving fails closed without it."""

from __future__ import annotations

import pytest

from exaserve.site import default_site_profile

_PROJECT = "/lus/flare/projects/example-project"
_FALLBACK = f"{_PROJECT}/eval-configured/models"


@pytest.fixture(autouse=True)
def fresh_site_profiles(monkeypatch):
    monkeypatch.delenv("EXASERVE_PROJECT_ROOT", raising=False)
    monkeypatch.delenv("EXASERVE_MODEL_STORAGE_PATH", raising=False)
    default_site_profile.cache_clear()
    yield
    default_site_profile.cache_clear()


@pytest.mark.parametrize(
    "exported",
    [
        {"EXASERVE_PROJECT_ROOT": _PROJECT},
        {"EXASERVE_MODEL_STORAGE_PATH": f"{_PROJECT}/models"},
        {"EXASERVE_PROJECT_ROOT": _PROJECT, "EXASERVE_MODEL_STORAGE_PATH": f"{_PROJECT}/models"},
    ],
)
def test_a_configured_model_path_makes_the_fallback_irrelevant(monkeypatch, exported):
    for name, value in exported.items():
        monkeypatch.setenv(name, value)

    serving = default_site_profile()
    with_fallback = default_site_profile(fallback_model_storage_path=_FALLBACK)

    assert with_fallback == serving
    assert with_fallback.site_profile_hash == serving.site_profile_hash
    assert serving.model_storage_path != _FALLBACK


def test_only_an_unconfigured_site_uses_the_fallback():
    with pytest.raises(RuntimeError, match="cannot derive the model storage path"):
        default_site_profile()

    assert default_site_profile(fallback_model_storage_path=_FALLBACK).model_storage_path == (
        _FALLBACK
    )
