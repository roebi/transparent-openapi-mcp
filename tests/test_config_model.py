"""Tests for transparent_openapi_mcp.config_model.

Covers R-CFG-001 (spec entry pairs specUrl+backendBaseUrl+prefix),
R-CFG-002 (multiple configs), R-CFG-005/006/007 (timeout hierarchy,
server-wide default is mandatory).
"""
import pytest
from pydantic import ValidationError

from transparent_openapi_mcp.config_model import Config, ConfigList, SpecEntry


def test_spec_entry_requires_prefix_spec_url_and_backend_url():
    entry = SpecEntry(
        prefix="tide",
        spec_url="https://internal.example/tide-openapi.json",
        backend_base_url="http://tide-openapi:8080",
    )
    assert entry.prefix == "tide"
    assert entry.spec_url == "https://internal.example/tide-openapi.json"
    assert entry.backend_base_url == "http://tide-openapi:8080"
    assert entry.timeout_seconds is None


def test_spec_entry_timeout_seconds_is_optional_and_settable():
    entry = SpecEntry(
        prefix="tide",
        spec_url="https://internal.example/tide-openapi.json",
        backend_base_url="http://tide-openapi:8080",
        timeout_seconds=120,
    )
    assert entry.timeout_seconds == 120


def test_spec_entry_missing_required_field_raises():
    with pytest.raises(ValidationError):
        SpecEntry(prefix="tide", spec_url="https://internal.example/x.json")


def test_config_holds_one_or_more_spec_entries():
    entry = SpecEntry(
        prefix="tide",
        spec_url="https://internal.example/tide-openapi.json",
        backend_base_url="http://tide-openapi:8080",
    )
    config = Config(name="tide-openapi-prod", specs=[entry])
    assert config.name == "tide-openapi-prod"
    assert len(config.specs) == 1
    assert config.default_timeout_seconds is None


def test_config_requires_at_least_one_spec_entry():
    with pytest.raises(ValidationError):
        Config(name="empty-config", specs=[])


def test_config_list_requires_mandatory_default_timeout_seconds():
    """R-CFG-007: server-wide default timeout is mandatory, no fallback."""
    entry = SpecEntry(
        prefix="tide",
        spec_url="https://internal.example/tide-openapi.json",
        backend_base_url="http://tide-openapi:8080",
    )
    config = Config(name="tide-openapi-prod", specs=[entry])
    with pytest.raises(ValidationError):
        ConfigList(configs=[config])  # missing default_timeout_seconds


def test_config_list_valid_with_default_timeout_seconds():
    entry = SpecEntry(
        prefix="tide",
        spec_url="https://internal.example/tide-openapi.json",
        backend_base_url="http://tide-openapi:8080",
    )
    config = Config(name="tide-openapi-prod", specs=[entry])
    config_list = ConfigList(
        configs=[config],
        default_timeout_seconds=60,
        preselected="tide-openapi-prod",
    )
    assert config_list.default_timeout_seconds == 60
    assert config_list.preselected == "tide-openapi-prod"


def test_config_list_preselected_is_optional():
    entry = SpecEntry(
        prefix="tide",
        spec_url="https://internal.example/tide-openapi.json",
        backend_base_url="http://tide-openapi:8080",
    )
    config = Config(name="tide-openapi-prod", specs=[entry])
    config_list = ConfigList(configs=[config], default_timeout_seconds=60)
    assert config_list.preselected is None


def test_effective_timeout_seconds_resolves_spec_entry_first():
    """R-FWD-002 resolution order: spec entry -> config -> config list."""
    entry = SpecEntry(
        prefix="tide",
        spec_url="https://internal.example/tide-openapi.json",
        backend_base_url="http://tide-openapi:8080",
        timeout_seconds=5,
    )
    config = Config(name="c", specs=[entry], default_timeout_seconds=300)
    config_list = ConfigList(configs=[config], default_timeout_seconds=60)
    assert config_list.effective_timeout_seconds(entry) == 5


def test_effective_timeout_seconds_falls_back_to_config_default():
    entry = SpecEntry(
        prefix="tide",
        spec_url="https://internal.example/tide-openapi.json",
        backend_base_url="http://tide-openapi:8080",
    )
    config = Config(name="c", specs=[entry], default_timeout_seconds=300)
    config_list = ConfigList(configs=[config], default_timeout_seconds=60)
    assert config_list.effective_timeout_seconds(entry) == 300


def test_effective_timeout_seconds_falls_back_to_config_list_default():
    entry = SpecEntry(
        prefix="tide",
        spec_url="https://internal.example/tide-openapi.json",
        backend_base_url="http://tide-openapi:8080",
    )
    config = Config(name="c", specs=[entry])
    config_list = ConfigList(configs=[config], default_timeout_seconds=60)
    assert config_list.effective_timeout_seconds(entry) == 60
