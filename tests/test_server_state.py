"""Tests for transparent_openapi_mcp.server_state.

Covers the BOOT sequence (R-BOOT-001..005), the unconfigured-state
guard (R-BOOT-003), listConfig/selectConfig (R-CFG-*), and tool
dispatch/forwarding (R-FWD-001/002). Uses httpx.MockTransport with a
URL-dispatching handler so no real network calls happen.
"""
import json

import httpx
import pytest

from transparent_openapi_mcp.server_state import ServerState, ServerNotConfiguredError, ToolExecutionError


CONFIG_LIST_URL = "https://internal.example/config-list.json"
SPEC_URL = "https://internal.example/tide-openapi.json"
BACKEND_URL = "http://tide-openapi:8080"

VALID_CONFIG_LIST = {
    "defaultTimeoutSeconds": 60,
    "preselected": "tide-openapi-prod",
    "configs": [
        {
            "name": "tide-openapi-prod",
            "specs": [
                {"prefix": "tide", "specUrl": SPEC_URL, "backendBaseUrl": BACKEND_URL}
            ],
        }
    ],
}

CONFIG_LIST_NO_PRESELECT = {
    "defaultTimeoutSeconds": 60,
    "configs": [
        {
            "name": "tide-openapi-prod",
            "specs": [
                {"prefix": "tide", "specUrl": SPEC_URL, "backendBaseUrl": BACKEND_URL}
            ],
        }
    ],
}

SIMPLE_OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "t", "version": "1"},
    "paths": {
        "/steps/click": {
            "post": {
                "operationId": "clickElement",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"elementId": {"type": "string"}},
                                "required": ["elementId"],
                            }
                        }
                    }
                },
            }
        }
    },
}


def _make_client(config_list_body=VALID_CONFIG_LIST, spec_reachable=True, backend_reachable=True, backend_response=None):
    def handler(request):
        url = str(request.url)
        if url == CONFIG_LIST_URL:
            return httpx.Response(200, json=config_list_body)
        if url == SPEC_URL:
            if not spec_reachable:
                raise httpx.ConnectError("connection refused", request=request)
            return httpx.Response(200, json=SIMPLE_OPENAPI_SPEC)
        if url.startswith(BACKEND_URL):
            if not backend_reachable:
                raise httpx.ConnectError("connection refused", request=request)
            return httpx.Response(200, json=backend_response or {"result": "ok"})
        raise AssertionError(f"unexpected URL in test: {url}")

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_boot_with_preselected_valid_config_becomes_configured():
    async with _make_client() as client:
        state = ServerState(client, CONFIG_LIST_URL)
        error = await state.boot()
    assert error is None
    assert state.is_configured()


@pytest.mark.asyncio
async def test_boot_without_preselected_stays_unconfigured():
    async with _make_client(config_list_body=CONFIG_LIST_NO_PRESELECT) as client:
        state = ServerState(client, CONFIG_LIST_URL)
        error = await state.boot()
    assert error is None
    assert not state.is_configured()


@pytest.mark.asyncio
async def test_boot_with_preselected_invalid_config_stays_unconfigured_and_returns_report():
    async with _make_client(spec_reachable=False) as client:
        state = ServerState(client, CONFIG_LIST_URL)
        error = await state.boot()
    assert error is not None
    assert "MCP CONFIG LOAD ERROR" in error
    assert not state.is_configured()


@pytest.mark.asyncio
async def test_boot_local_override_takes_precedence_over_config_list_preselected():
    """R-BOOT-001: the local mounted config file's preselection wins
    over the remote config-list's own (optional) preselected field."""
    other_config_list = {
        "defaultTimeoutSeconds": 60,
        "preselected": "tide-openapi-prod",
        "configs": [
            {"name": "tide-openapi-prod", "specs": [{"prefix": "tide", "specUrl": SPEC_URL, "backendBaseUrl": BACKEND_URL}]},
            {"name": "other", "specs": [{"prefix": "other", "specUrl": SPEC_URL, "backendBaseUrl": BACKEND_URL}]},
        ],
    }
    async with _make_client(config_list_body=other_config_list) as client:
        state = ServerState(client, CONFIG_LIST_URL)
        error = await state.boot(preselected_override="other")
    assert error is None
    assert state.is_configured()
    assert state.list_configs() == ["tide-openapi-prod", "other"]


@pytest.mark.asyncio
async def test_list_tools_unconfigured_only_exposes_control_tools():
    async with _make_client(config_list_body=CONFIG_LIST_NO_PRESELECT) as client:
        state = ServerState(client, CONFIG_LIST_URL)
        await state.boot()
        tools = state.list_tools()
    assert {t.name for t in tools} == {"listConfig", "selectConfig"}


@pytest.mark.asyncio
async def test_list_tools_configured_includes_openapi_derived_tools():
    async with _make_client() as client:
        state = ServerState(client, CONFIG_LIST_URL)
        await state.boot()
        tools = state.list_tools()
    assert {"listConfig", "selectConfig", "tide_clickElement"} <= {t.name for t in tools}


@pytest.mark.asyncio
async def test_call_tool_list_config_returns_config_names():
    async with _make_client(config_list_body=CONFIG_LIST_NO_PRESELECT) as client:
        state = ServerState(client, CONFIG_LIST_URL)
        await state.boot()
        result = await state.call_tool("listConfig", {})
    assert result == ["tide-openapi-prod"]


@pytest.mark.asyncio
async def test_call_tool_select_config_activates_it():
    async with _make_client(config_list_body=CONFIG_LIST_NO_PRESELECT) as client:
        state = ServerState(client, CONFIG_LIST_URL)
        await state.boot()
        assert not state.is_configured()
        await state.call_tool("selectConfig", {"name": "tide-openapi-prod"})
    assert state.is_configured()


@pytest.mark.asyncio
async def test_call_tool_select_config_raises_on_validation_failure():
    async with _make_client(config_list_body=CONFIG_LIST_NO_PRESELECT, spec_reachable=False) as client:
        state = ServerState(client, CONFIG_LIST_URL)
        await state.boot()
        with pytest.raises(ToolExecutionError, match="MCP CONFIG LOAD ERROR"):
            await state.call_tool("selectConfig", {"name": "tide-openapi-prod"})


@pytest.mark.asyncio
async def test_call_tool_openapi_derived_raises_when_unconfigured():
    async with _make_client(config_list_body=CONFIG_LIST_NO_PRESELECT) as client:
        state = ServerState(client, CONFIG_LIST_URL)
        await state.boot()
        with pytest.raises(ServerNotConfiguredError):
            await state.call_tool("tide_clickElement", {"elementId": "btn-1"})


@pytest.mark.asyncio
async def test_call_tool_openapi_derived_forwards_and_returns_backend_response():
    async with _make_client(backend_response={"result": "clicked"}) as client:
        state = ServerState(client, CONFIG_LIST_URL)
        await state.boot()
        result = await state.call_tool("tide_clickElement", {"elementId": "btn-1"})
    assert result == {"result": "clicked"}


@pytest.mark.asyncio
async def test_call_tool_unknown_tool_name_raises():
    async with _make_client() as client:
        state = ServerState(client, CONFIG_LIST_URL)
        await state.boot()
        with pytest.raises(ToolExecutionError, match="unknown tool"):
            await state.call_tool("does_not_exist", {})
