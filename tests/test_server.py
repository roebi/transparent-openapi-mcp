"""Tests for transparent_openapi_mcp.server's result-wrapping logic.

Covers turning ServerState.call_tool()'s outcome into a proper MCP
CallToolResult: success becomes text content, ServerNotConfiguredError
and ToolExecutionError become an error result carrying the message
(e.g. the R-BOOT-005 report) so the caller sees it directly.
"""
import json

import httpx
import pytest

from transparent_openapi_mcp.server import handle_call_tool, handle_list_tools
from transparent_openapi_mcp.server_state import ServerState

CONFIG_LIST_URL = "https://internal.example/config-list.json"
SPEC_URL = "https://internal.example/tide-openapi.json"
BACKEND_URL = "http://tide-openapi:8080"

CONFIG_LIST_NO_PRESELECT = {
    "defaultTimeoutSeconds": 60,
    "configs": [
        {"name": "tide-openapi-prod", "specs": [{"prefix": "tide", "specUrl": SPEC_URL, "backendBaseUrl": BACKEND_URL}]}
    ],
}

SIMPLE_OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "t", "version": "1"},
    "paths": {"/steps/click": {"post": {"operationId": "clickElement"}}},
}


def _make_client():
    def handler(request):
        url = str(request.url)
        if url == CONFIG_LIST_URL:
            return httpx.Response(200, json=CONFIG_LIST_NO_PRESELECT)
        if url == SPEC_URL:
            return httpx.Response(200, json=SIMPLE_OPENAPI_SPEC)
        if url.startswith(BACKEND_URL):
            return httpx.Response(200, json={"result": "ok"})
        raise AssertionError(f"unexpected URL: {url}")

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_handle_list_tools_delegates_to_state():
    async with _make_client() as client:
        state = ServerState(client, CONFIG_LIST_URL)
        await state.boot()
        tools = await handle_list_tools(state)
    assert {"listConfig", "selectConfig"} == {t.name for t in tools}


@pytest.mark.asyncio
async def test_handle_call_tool_success_returns_text_content_not_error():
    async with _make_client() as client:
        state = ServerState(client, CONFIG_LIST_URL)
        await state.boot()
        result = await handle_call_tool(state, "listConfig", {})
    assert result.is_error is False
    assert result.content[0].type == "text"
    assert "tide-openapi-prod" in result.content[0].text


@pytest.mark.asyncio
async def test_handle_call_tool_unconfigured_returns_error_result():
    async with _make_client() as client:
        state = ServerState(client, CONFIG_LIST_URL)
        await state.boot()
        result = await handle_call_tool(state, "tide_clickElement", {})
    assert result.is_error is True
    assert "No backend configuration" in result.content[0].text


@pytest.mark.asyncio
async def test_handle_call_tool_select_config_failure_returns_error_result_with_report():
    def handler(request):
        url = str(request.url)
        if url == CONFIG_LIST_URL:
            return httpx.Response(200, json=CONFIG_LIST_NO_PRESELECT)
        raise httpx.ConnectError("connection refused", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        state = ServerState(client, CONFIG_LIST_URL)
        await state.boot()
        result = await handle_call_tool(state, "selectConfig", {"name": "tide-openapi-prod"})
    assert result.is_error is True
    assert "MCP CONFIG LOAD ERROR" in result.content[0].text


@pytest.mark.asyncio
async def test_handle_call_tool_success_forwarding_returns_backend_json_as_text():
    async with _make_client() as client:
        state = ServerState(client, CONFIG_LIST_URL)
        await state.boot()
        await handle_call_tool(state, "selectConfig", {"name": "tide-openapi-prod"})
        result = await handle_call_tool(state, "tide_clickElement", {})
    assert result.is_error is False
    assert json.loads(result.content[0].text) == {"result": "ok"}
