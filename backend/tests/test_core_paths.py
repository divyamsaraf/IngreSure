"""
Unit tests for core path resolution. Run from backend directory:
  cd backend && python -m pytest tests/test_core_paths.py -v
"""
import pytest
from pathlib import Path


def test_backend_is_current_or_on_path():
    """Ensure tests run with backend as cwd or on path so 'core' resolves."""
    try:
        from core import config
    except ImportError as e:
        pytest.skip("Run tests from backend directory: cd backend && python -m pytest ...")
        return
    assert config._BACKEND_DIR.is_dir()
    assert (config._BACKEND_DIR / "core").is_dir()
    assert config._REPO_ROOT.is_dir()
    assert config._REPO_ROOT.name != "core"


def test_ontology_path_resolution():
    """Ontology path is repo_root/data/ontology.json."""
    from core.config import get_ontology_path, _REPO_ROOT
    path = get_ontology_path()
    assert path == _REPO_ROOT / "data" / "ontology.json"
    assert path.suffix == ".json"
    # Data may or may not exist in dev; path must be deterministic
    assert "data" in path.parts
    assert "ontology.json" in path.name


def test_restrictions_path_resolution():
    """Restrictions path is repo_root/data/restrictions.json."""
    from core.config import get_restrictions_path, _REPO_ROOT
    path = get_restrictions_path()
    assert path == _REPO_ROOT / "data" / "restrictions.json"
    assert path.suffix == ".json"
    assert "data" in path.parts
    assert "restrictions.json" in path.name


def test_ontology_file_exists_when_data_present():
    """When data/ exists in repo, ontology.json should exist (Phase 2)."""
    from core.config import get_ontology_path, _REPO_ROOT
    data_dir = _REPO_ROOT / "data"
    if not data_dir.exists():
        pytest.skip("data/ directory not found (run from repo root with Phase 2 data)")
    path = get_ontology_path()
    assert path.exists(), f"Expected {path} to exist for path resolution tests"


def test_restrictions_file_exists_when_data_present():
    """When data/ exists, restrictions.json should exist."""
    from core.config import get_restrictions_path, _REPO_ROOT
    data_dir = _REPO_ROOT / "data"
    if not data_dir.exists():
        pytest.skip("data/ directory not found")
    path = get_restrictions_path()
    assert path.exists(), f"Expected {path} to exist"


def test_ingredient_registry_loads_from_resolved_path():
    """IngredientRegistry uses config path and loads when file exists."""
    from core.config import get_ontology_path
    from core.ontology.ingredient_registry import IngredientRegistry
    if not get_ontology_path().exists():
        pytest.skip("ontology.json not found")
    reg = IngredientRegistry()
    assert len(reg) > 0
    assert reg.get_version() and len(reg.get_version()) >= 1


def test_restriction_registry_loads_from_resolved_path():
    """RestrictionRegistry uses config path and loads when file exists."""
    from core.config import get_restrictions_path
    from core.restrictions.restriction_registry import RestrictionRegistry
    if not get_restrictions_path().exists():
        pytest.skip("restrictions.json not found")
    reg = RestrictionRegistry()
    assert len(reg.list_ids()) > 0
    assert reg.get("vegan") is not None
    assert reg.get("no_onion") is not None
