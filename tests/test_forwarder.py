"""Tests for transparent_openapi_mcp.forwarder.

Covers R-FWD-001 (forward to the operation's paired backend URL using
its path/method/params/body, return the response) and R-FWD-002
(apply the resolved timeout).
"""
import json

import httpx
import pytest

from transparent_openapi_mcp.config_model import SpecEntry
from transparent_openapi_mcp.forwarder import forward_call
from transparent_openapi_mcp.openapi_parser import Operation


def _client_with_handler(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_forward_call_builds_url_from_backend_base_url_and_path():
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"ok": True})

    op = Operation(operation_id="clickElement", path="/steps/click", method="post")
    entry = SpecEntry(prefix="tide", spec_url="https://x/spec.json", backend_base_url="http://tide-openapi:8080")

    async with _client_with_handler(handler) as client:
        await forward_call(client, operation=op, entry=entry, timeout_seconds=30, arguments={})

    assert captured["url"] == "http://tide-openapi:8080/steps/click"


@pytest.mark.asyncio
async def test_forward_call_substitutes_path_parameters():
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"ok": True})

    op = Operation(
        operation_id="getElement",
        path="/steps/{elementId}",
        method="get",
        parameters=[{"name": "elementId", "in": "path", "required": True, "schema": {"type": "string"}}],
    )
    entry = SpecEntry(prefix="tide", spec_url="https://x/spec.json", backend_base_url="http://tide-openapi:8080")

    async with _client_with_handler(handler) as client:
        await forward_call(
            client, operation=op, entry=entry, timeout_seconds=30, arguments={"elementId": "btn-1"}
        )

    assert captured["url"] == "http://tide-openapi:8080/steps/btn-1"


@pytest.mark.asyncio
async def test_forward_call_sends_query_parameters():
    captured = {}

    def handler(request):
        captured["query"] = dict(request.url.params)
        return httpx.Response(200, json={"ok": True})

    op = Operation(
        operation_id="waitForBatch",
        path="/steps/wait",
        method="post",
        parameters=[{"name": "timeoutSeconds", "in": "query", "required": False, "schema": {"type": "integer"}}],
    )
    entry = SpecEntry(prefix="tide", spec_url="https://x/spec.json", backend_base_url="http://tide-openapi:8080")

    async with _client_with_handler(handler) as client:
        await forward_call(
            client, operation=op, entry=entry, timeout_seconds=30, arguments={"timeoutSeconds": "120"}
        )

    assert captured["query"] == {"timeoutSeconds": "120"}


@pytest.mark.asyncio
async def test_forward_call_sends_json_body_from_body_fields():
    captured = {}

    def handler(request):
        captured["json"] = json.loads(request.content) if request.content else None
        return httpx.Response(200, json={"ok": True})

    op = Operation(
        operation_id="clickElement",
        path="/steps/click",
        method="post",
        request_body_schema={
            "type": "object",
            "properties": {"elementId": {"type": "string"}},
            "required": ["elementId"],
        },
    )
    entry = SpecEntry(prefix="tide", spec_url="https://x/spec.json", backend_base_url="http://tide-openapi:8080")

    async with _client_with_handler(handler) as client:
        await forward_call(
            client, operation=op, entry=entry, timeout_seconds=30, arguments={"elementId": "btn-1"}
        )

    assert captured["json"] == {"elementId": "btn-1"}


@pytest.mark.asyncio
async def test_forward_call_uses_operation_http_method():
    captured = {}

    def handler(request):
        captured["method"] = request.method
        return httpx.Response(200, json={"ok": True})

    op = Operation(operation_id="clickElement", path="/steps/click", method="post")
    entry = SpecEntry(prefix="tide", spec_url="https://x/spec.json", backend_base_url="http://tide-openapi:8080")

    async with _client_with_handler(handler) as client:
        await forward_call(client, operation=op, entry=entry, timeout_seconds=30, arguments={})

    assert captured["method"] == "POST"


@pytest.mark.asyncio
async def test_forward_call_applies_resolved_timeout():
    captured = {}

    def handler(request):
        captured["timeout"] = request.extensions.get("timeout")
        return httpx.Response(200, json={"ok": True})

    op = Operation(operation_id="waitForBatch", path="/steps/wait", method="post")
    entry = SpecEntry(prefix="tide", spec_url="https://x/spec.json", backend_base_url="http://tide-openapi:8080")

    async with _client_with_handler(handler) as client:
        await forward_call(client, operation=op, entry=entry, timeout_seconds=300, arguments={})

    assert captured["timeout"]["read"] == 300


@pytest.mark.asyncio
async def test_forward_call_returns_response_body():
    def handler(request):
        return httpx.Response(200, json={"result": "clicked"})

    op = Operation(operation_id="clickElement", path="/steps/click", method="post")
    entry = SpecEntry(prefix="tide", spec_url="https://x/spec.json", backend_base_url="http://tide-openapi:8080")

    async with _client_with_handler(handler) as client:
        result = await forward_call(client, operation=op, entry=entry, timeout_seconds=30, arguments={})

    assert result.status_code == 200
    assert result.json() == {"result": "clicked"}
