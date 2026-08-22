"""Tests for transparent_openapi_mcp.errors.

Covers R-BOOT-005: the config validation failure report must name
which URL(s) failed and why, state which config-list URL to edit, and
give guidance on a valid value - so a person or agent can fix it
without further back-and-forth.
"""
from transparent_openapi_mcp.errors import UrlFailure, format_config_load_error


def test_url_failure_holds_url_and_reason():
    failure = UrlFailure(url="https://example/x.json", reason="unreachable (connection refused)")
    assert failure.url == "https://example/x.json"
    assert failure.reason == "unreachable (connection refused)"


def test_format_config_load_error_names_the_server():
    report = format_config_load_error(
        config_name="tide-openapi-prod",
        failures=[UrlFailure(url="https://x/spec.json", reason="unreachable")],
        config_list_url="https://internal.example/config-list.json",
    )
    assert "MCP CONFIG LOAD ERROR" in report
    assert "transparent-openapi-mcp" in report


def test_format_config_load_error_names_config_and_each_failed_url():
    report = format_config_load_error(
        config_name="tide-openapi-prod",
        failures=[
            UrlFailure(url="https://x/spec.json", reason="unreachable (connection refused)"),
            UrlFailure(url="http://backend:8080", reason="invalid JSON"),
        ],
        config_list_url="https://internal.example/config-list.json",
    )
    assert "tide-openapi-prod" in report
    assert "https://x/spec.json" in report
    assert "unreachable (connection refused)" in report
    assert "http://backend:8080" in report
    assert "invalid JSON" in report


def test_format_config_load_error_states_config_list_url_to_fix():
    report = format_config_load_error(
        config_name="c",
        failures=[UrlFailure(url="https://x/spec.json", reason="unreachable")],
        config_list_url="https://internal.example/config-list.json",
    )
    assert "https://internal.example/config-list.json" in report


def test_format_config_load_error_gives_valid_value_guidance():
    report = format_config_load_error(
        config_name="c",
        failures=[UrlFailure(url="https://x/spec.json", reason="unreachable")],
        config_list_url="https://internal.example/config-list.json",
    )
    assert "specUrl" in report or "spec URL" in report
    assert "backendBaseUrl" in report or "backend" in report
