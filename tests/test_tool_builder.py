"""Tests for transparent_openapi_mcp.tool_builder.

Covers R-TOOLS-001 (one MCP tool per operation, schema derived
directly from the operation), R-TOOLS-003 (tool names namespaced by
prefix).
"""
from transparent_openapi_mcp.openapi_parser import Operation
from transparent_openapi_mcp.tool_builder import build_tool, build_tools


def test_build_tool_names_with_prefix_underscore_operation_id():
    """R-TOOLS-003."""
    op = Operation(operation_id="clickElement", path="/steps/click", method="post")
    tool = build_tool(op, prefix="tide")
    assert tool.name == "tide_clickElement"


def test_build_tool_uses_summary_as_description():
    op = Operation(
        operation_id="clickElement",
        path="/steps/click",
        method="post",
        summary="Click a GUI element",
    )
    tool = build_tool(op, prefix="tide")
    assert tool.description == "Click a GUI element"


def test_build_tool_input_schema_includes_request_body_properties():
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
    tool = build_tool(op, prefix="tide")
    assert tool.input_schema["type"] == "object"
    assert tool.input_schema["properties"]["elementId"]["type"] == "string"
    assert "elementId" in tool.input_schema["required"]


def test_build_tool_input_schema_includes_query_parameters():
    op = Operation(
        operation_id="waitForBatch",
        path="/steps/wait",
        method="post",
        parameters=[
            {"name": "timeoutSeconds", "in": "query", "required": False, "schema": {"type": "integer"}}
        ],
    )
    tool = build_tool(op, prefix="tide")
    assert tool.input_schema["properties"]["timeoutSeconds"]["type"] == "integer"
    assert "timeoutSeconds" not in tool.input_schema["required"]


def test_build_tool_required_parameter_is_in_required_list():
    op = Operation(
        operation_id="waitForBatch",
        path="/steps/wait",
        method="post",
        parameters=[
            {"name": "batchId", "in": "query", "required": True, "schema": {"type": "string"}}
        ],
    )
    tool = build_tool(op, prefix="tide")
    assert "batchId" in tool.input_schema["required"]


def test_build_tool_merges_parameters_and_request_body():
    op = Operation(
        operation_id="clickWithTimeout",
        path="/steps/click",
        method="post",
        parameters=[
            {"name": "timeoutSeconds", "in": "query", "required": False, "schema": {"type": "integer"}}
        ],
        request_body_schema={
            "type": "object",
            "properties": {"elementId": {"type": "string"}},
            "required": ["elementId"],
        },
    )
    tool = build_tool(op, prefix="tide")
    assert set(tool.input_schema["properties"].keys()) == {"timeoutSeconds", "elementId"}
    assert tool.input_schema["required"] == ["elementId"]


def test_build_tool_with_no_parameters_or_body_has_empty_object_schema():
    op = Operation(operation_id="noop", path="/steps/noop", method="post")
    tool = build_tool(op, prefix="tide")
    assert tool.input_schema == {"type": "object", "properties": {}, "required": []}


def test_build_tools_maps_multiple_operations():
    ops = [
        Operation(operation_id="a", path="/a", method="post"),
        Operation(operation_id="b", path="/b", method="post"),
    ]
    tools = build_tools(ops, prefix="tide")
    assert {t.name for t in tools} == {"tide_a", "tide_b"}


def test_build_tools_returns_empty_list_for_empty_operations():
    assert build_tools([], prefix="tide") == []
