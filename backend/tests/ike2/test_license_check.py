"""Item 1 Prompt 4: license_check allow / deny / missing metadata."""
from pathlib import Path

import pytest

from core.knowledge.ike2.etl.license_check import (
    clear_allowlist_cache,
    license_check,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_allowlist_cache()
    yield
    clear_allowlist_cache()


def test_missing_license_metadata_denies():
    d = license_check("produce_catalog", None)
    assert d.allowed is False
    assert d.reason == "missing_license_metadata"
    assert not d


def test_empty_license_string_denies():
    d = license_check("produce_catalog", "  ")
    assert d.allowed is False
    assert d.reason == "missing_license_metadata"


def test_allowlisted_global_license_allows():
    d = license_check("some_new_source", "CC0-1.0")
    assert d.allowed is True
    assert d.reason == "allow_global_license"


def test_ogl_uk_and_canada_are_allowlisted():
    assert license_check("cofid", "OGL-UK-3.0").allowed is True
    assert license_check("canadian_nutrient_file", "OGL-Canada-2.0").allowed is True
    assert license_check("new_local_names", "OGL-UK-3.0").allowed is True
    assert license_check("new_local_names", "OGL-Canada-2.0").allowed is True


def test_unknown_license_denies():
    d = license_check("some_new_source", "Proprietary-All-Rights")
    assert d.allowed is False
    assert "license_not_allowlisted" in d.reason


def test_source_specific_allowlist():
    assert license_check("produce_catalog", "CC0-1.0").allowed is True
    d = license_check("produce_catalog", "CC-BY-4.0")
    # CC-BY-4.0 is global-allowed but produce_catalog has its own list
    assert d.allowed is False
    assert "license_not_allowlisted_for_source" in d.reason


def test_custom_allowlist_path(tmp_path: Path):
    path = tmp_path / "allow.json"
    path.write_text(
        '{"allowed_licenses": ["MIT"], "source_licenses": {}}',
        encoding="utf-8",
    )
    assert license_check("x", "MIT", allowlist_path=path).allowed is True
    assert license_check("x", "CC0-1.0", allowlist_path=path).allowed is False
