"""Tests for transparent_openapi_mcp.config_loader.

Covers R-CFG-004: the server loads the config list from a URL to a
raw JSON file at startup. Uses httpx.MockTransport so no real network
calls happen.
"""
import httpx
import pytest

from transparent_openapi_mcp.config_loader import ConfigLoadError, load_config_list


VALID_CONFIG_LIST_JSON = """
{
  "defaultTimeoutSeconds": 60,
  "preselected": "tide-openapi-prod",
  "configs": [
    {
      "name": "tide-openapi-prod",
      "defaultTimeoutSeconds": 300,
      "specs": [
        {
          "prefix": "tide",
          "specUrl": "https://internal.example/tide-openapi.json",
          "backendBaseUrl": "http://tide-openapi:8080"
        }
      ]
    }
  ]
}
"""


def _client_with_handler(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_load_config_list_parses_valid_json_into_config_list():
    def handler(request):
        return httpx.Response(200, content=VALID_CONFIG_LIST_JSON)

    async with _client_with_handler(handler) as client:
        config_list = await load_config_list(client, "https://internal.example/config-list.json")

    assert config_list.default_timeout_seconds == 60
    assert config_list.preselected == "tide-openapi-prod"
    assert len(config_list.configs) == 1
    assert config_list.configs[0].name == "tide-openapi-prod"
    assert config_list.configs[0].specs[0].prefix == "tide"
    assert config_list.configs[0].specs[0].spec_url == "https://internal.example/tide-openapi.json"
    assert config_list.configs[0].specs[0].backend_base_url == "http://tide-openapi:8080"


@pytest.mark.asyncio
async def test_load_config_list_uses_camel_case_json_field_names():
    """R-CFG-003: JSON syntax matches Claude Code MCP config conventions (camelCase)."""
    def handler(request):
        return httpx.Response(200, content=VALID_CONFIG_LIST_JSON)

    async with _client_with_handler(handler) as client:
        config_list = await load_config_list(client, "https://internal.example/config-list.json")

    # snake_case Python attributes populated from camelCase JSON keys
    assert config_list.configs[0].default_timeout_seconds == 300


@pytest.mark.asyncio
async def test_load_config_list_raises_on_unreachable_url():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    async with _client_with_handler(handler) as client:
        with pytest.raises(ConfigLoadError, match="unreachable"):
            await load_config_list(client, "https://internal.example/config-list.json")


@pytest.mark.asyncio
async def test_load_config_list_raises_on_http_error_status():
    def handler(request):
        return httpx.Response(404)

    async with _client_with_handler(handler) as client:
        with pytest.raises(ConfigLoadError, match="404"):
            await load_config_list(client, "https://internal.example/config-list.json")


@pytest.mark.asyncio
async def test_load_config_list_raises_on_invalid_json():
    def handler(request):
        return httpx.Response(200, content=b"not json")

    async with _client_with_handler(handler) as client:
        with pytest.raises(ConfigLoadError, match="invalid JSON"):
            await load_config_list(client, "https://internal.example/config-list.json")


@pytest.mark.asyncio
async def test_load_config_list_raises_on_schema_mismatch():
    """Missing mandatory defaultTimeoutSeconds (R-CFG-007) surfaces as ConfigLoadError."""
    def handler(request):
        return httpx.Response(200, json={"configs": []})

    async with _client_with_handler(handler) as client:
        with pytest.raises(ConfigLoadError):
            await load_config_list(client, "https://internal.example/config-list.json")
