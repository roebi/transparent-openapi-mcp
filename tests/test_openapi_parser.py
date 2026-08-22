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


SPEC_WITH_REF_REQUEST_BODY = {
    "openapi": "3.0.0",
    "info": {"title": "t", "version": "1"},
    "components": {
        "schemas": {
            "ClickRequest": {
                "type": "object",
                "properties": {"elementId": {"type": "string"}},
                "required": ["elementId"],
            }
        }
    },
    "paths": {
        "/steps/click": {
            "post": {
                "operationId": "clickElement",
                "requestBody": {
                    "content": {
                        "application/json": {"schema": {"$ref": "#/components/schemas/ClickRequest"}}
                    }
                },
            }
        }
    },
}


@pytest.mark.asyncio
async def test_fetch_operations_resolves_ref_in_request_body_schema():
    def handler(request):
        return httpx.Response(200, json=SPEC_WITH_REF_REQUEST_BODY)

    async with _client_with_handler(handler) as client:
        operations = await fetch_operations(client, "https://x/spec.json")

    op = operations[0]
    assert op.request_body_schema["type"] == "object"
    assert op.request_body_schema["properties"]["elementId"]["type"] == "string"
    assert op.request_body_schema["required"] == ["elementId"]


SPEC_WITH_REF_PARAMETER_SCHEMA = {
    "openapi": "3.0.0",
    "info": {"title": "t", "version": "1"},
    "components": {"schemas": {"TimeoutSchema": {"type": "integer", "minimum": 0}}},
    "paths": {
        "/steps/wait": {
            "post": {
                "operationId": "waitForBatch",
                "parameters": [
                    {
                        "name": "timeoutSeconds",
                        "in": "query",
                        "required": False,
                        "schema": {"$ref": "#/components/schemas/TimeoutSchema"},
                    }
                ],
            }
        }
    },
}


@pytest.mark.asyncio
async def test_fetch_operations_resolves_ref_in_parameter_schema():
    def handler(request):
        return httpx.Response(200, json=SPEC_WITH_REF_PARAMETER_SCHEMA)

    async with _client_with_handler(handler) as client:
        operations = await fetch_operations(client, "https://x/spec.json")

    op = operations[0]
    assert op.parameters[0]["schema"]["type"] == "integer"
    assert op.parameters[0]["schema"]["minimum"] == 0


SPEC_WITH_REF_WHOLE_PARAMETER = {
    "openapi": "3.0.0",
    "info": {"title": "t", "version": "1"},
    "components": {
        "parameters": {
            "ElementIdParam": {
                "name": "elementId",
                "in": "query",
                "required": True,
                "schema": {"type": "string"},
            }
        }
    },
    "paths": {
        "/steps/click": {
            "post": {
                "operationId": "clickElement",
                "parameters": [{"$ref": "#/components/parameters/ElementIdParam"}],
            }
        }
    },
}


@pytest.mark.asyncio
async def test_fetch_operations_resolves_whole_parameter_ref():
    def handler(request):
        return httpx.Response(200, json=SPEC_WITH_REF_WHOLE_PARAMETER)

    async with _client_with_handler(handler) as client:
        operations = await fetch_operations(client, "https://x/spec.json")

    op = operations[0]
    assert op.parameters[0]["name"] == "elementId"
    assert op.parameters[0]["required"] is True
    assert op.parameters[0]["schema"]["type"] == "string"


SPEC_WITH_NESTED_REF = {
    "openapi": "3.0.0",
    "info": {"title": "t", "version": "1"},
    "components": {
        "schemas": {
            "Coordinates": {
                "type": "object",
                "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
            },
            "ClickRequest": {
                "type": "object",
                "properties": {"position": {"$ref": "#/components/schemas/Coordinates"}},
            },
        }
    },
    "paths": {
        "/steps/click": {
            "post": {
                "operationId": "clickElement",
                "requestBody": {
                    "content": {
                        "application/json": {"schema": {"$ref": "#/components/schemas/ClickRequest"}}
                    }
                },
            }
        }
    },
}


@pytest.mark.asyncio
async def test_fetch_operations_resolves_nested_ref_inside_properties():
    def handler(request):
        return httpx.Response(200, json=SPEC_WITH_NESTED_REF)

    async with _client_with_handler(handler) as client:
        operations = await fetch_operations(client, "https://x/spec.json")

    op = operations[0]
    position_schema = op.request_body_schema["properties"]["position"]
    assert position_schema["type"] == "object"
    assert position_schema["properties"]["x"]["type"] == "integer"


SPEC_WITH_CIRCULAR_REF = {
    "openapi": "3.0.0",
    "info": {"title": "t", "version": "1"},
    "components": {
        "schemas": {
            "TreeNode": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "children": {"type": "array", "items": {"$ref": "#/components/schemas/TreeNode"}},
                },
            }
        }
    },
    "paths": {
        "/steps/tree": {
            "post": {
                "operationId": "setTree",
                "requestBody": {
                    "content": {
                        "application/json": {"schema": {"$ref": "#/components/schemas/TreeNode"}}
                    }
                },
            }
        }
    },
}


@pytest.mark.asyncio
async def test_fetch_operations_handles_circular_ref_without_hanging():
    def handler(request):
        return httpx.Response(200, json=SPEC_WITH_CIRCULAR_REF)

    async with _client_with_handler(handler) as client:
        operations = await fetch_operations(client, "https://x/spec.json")

    op = operations[0]
    assert op.request_body_schema["type"] == "object"
    assert op.request_body_schema["properties"]["label"]["type"] == "string"
    children_items = op.request_body_schema["properties"]["children"]["items"]
    # The cycle back to TreeNode is left as an unresolved $ref rather
    # than expanded infinitely.
    assert "$ref" in children_items
