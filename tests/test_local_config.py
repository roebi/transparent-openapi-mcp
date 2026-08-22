"""Tests for transparent_openapi_mcp.local_config.

Covers the mounted local config file (R-DEPLOY-002): contains the
config-list URL and, optionally, a preselected config name
(R-BOOT-001).
"""
from transparent_openapi_mcp.local_config import LocalConfig, load_local_config


def test_local_config_parses_config_list_url_and_preselected():
    local = LocalConfig.model_validate_json(
        '{"configListUrl": "https://x/config-list.json", "preselected": "tide-openapi-prod"}'
    )
    assert local.config_list_url == "https://x/config-list.json"
    assert local.preselected == "tide-openapi-prod"


def test_local_config_preselected_is_optional():
    local = LocalConfig.model_validate_json('{"configListUrl": "https://x/config-list.json"}')
    assert local.preselected is None


def test_load_local_config_reads_from_file_path(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text('{"configListUrl": "https://x/config-list.json"}')
    local = load_local_config(str(config_file))
    assert local.config_list_url == "https://x/config-list.json"
