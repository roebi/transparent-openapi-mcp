"""Tests for transparent_openapi_mcp.openapi_parser.

Covers the fetch+parse step feeding R-TOOLS-001: extract operations
(path, method, operationId, parameters, requestBody) from an OpenAPI
v3 JSON document. Uses httpx.MockTransport so no real network calls
happen.
"""
import httpx
import pytest

from transparent_openapi_mcp.openapi_parser import Operation, fetch_operations


SIMPLE_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Tide Test Steps", "version": "1.0.0"},
    "paths": {
        "/steps/click": {
            "post": {
                "operationId": "clickElement",
                "summary": "Click a GUI element",
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
                "parameters": [],
            }
        },
        "/steps/wait": {
            "post": {
                "operationId": "waitForBatch",
                "parameters": [
                    {
                        "name": "timeoutSeconds",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "integer"},
                    }
                ],
            }
        },
    },
}


def _client_with_handler(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_fetch_operations_extracts_one_operation_per_path_method():
    def handler(request):
        return httpx.Response(200, json=SIMPLE_SPEC)

    async with _client_with_handler(handler) as client:
        operations = await fetch_operations(client, "https://x/spec.json")

    assert len(operations) == 2
    op_ids = {op.operation_id for op in operations}
    assert op_ids == {"clickElement", "waitForBatch"}


@pytest.mark.asyncio
async def test_fetch_operations_captures_path_and_method():
    def handler(request):
        return httpx.Response(200, json=SIMPLE_SPEC)

    async with _client_with_handler(handler) as client:
        operations = await fetch_operations(client, "https://x/spec.json")

    click = next(op for op in operations if op.operation_id == "clickElement")
    assert click.path == "/steps/click"
    assert click.method == "post"


@pytest.mark.asyncio
async def test_fetch_operations_captures_request_body_schema():
    def handler(request):
        return httpx.Response(200, json=SIMPLE_SPEC)

    async with _client_with_handler(handler) as client:
        operations = await fetch_operations(client, "https://x/spec.json")

    click = next(op for op in operations if op.operation_id == "clickElement")
    assert click.request_body_schema is not None
    assert click.request_body_schema["properties"]["elementId"]["type"] == "string"


@pytest.mark.asyncio
async def test_fetch_operations_captures_parameters():
    def handler(request):
        return httpx.Response(200, json=SIMPLE_SPEC)

    async with _client_with_handler(handler) as client:
        operations = await fetch_operations(client, "https://x/spec.json")

    wait = next(op for op in operations if op.operation_id == "waitForBatch")
    assert len(wait.parameters) == 1
    assert wait.parameters[0]["name"] == "timeoutSeconds"


@pytest.mark.asyncio
async def test_operation_without_request_body_has_none_schema():
    def handler(request):
        return httpx.Response(200, json=SIMPLE_SPEC)

    async with _client_with_handler(handler) as client:
        operations = await fetch_operations(client, "https://x/spec.json")

    wait = next(op for op in operations if op.operation_id == "waitForBatch")
    assert wait.request_body_schema is None
