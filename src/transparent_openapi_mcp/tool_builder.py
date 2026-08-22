"""OpenAPI operation to MCP tool mapping (R-TOOLS-001, R-TOOLS-003).

Pure function of an Operation - no operation is special-cased, so a
changed spec (extracted by openapi_parser.py into changed Operations)
yields a changed tool list with zero code changes here (R-TOOLS-002).
"""
from __future__ import annotations

from typing import Any

from mcp.types import Tool

from transparent_openapi_mcp.openapi_parser import Operation


def build_tool(operation: Operation, *, prefix: str) -> Tool:
    """Build one MCP Tool from one OpenAPI operation.

    R-TOOLS-003: name is `<prefix>_<operationId>`.
    Input schema is derived directly from the operation's parameters
    and request body - query/path parameters and request body
    properties are merged into one flat object schema, since MCP tool
    calls pass a single arguments object.
    """
    return Tool(
        name=f"{prefix}_{operation.operation_id}",
        description=operation.summary,
        inputSchema=_build_input_schema(operation),
    )


def build_tools(operations: list[Operation], *, prefix: str) -> list[Tool]:
    """Build one MCP Tool per operation (R-TOOLS-001)."""
    return [build_tool(op, prefix=prefix) for op in operations]


def _build_input_schema(operation: Operation) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param in operation.parameters:
        properties[param["name"]] = param.get("schema", {})
        if param.get("required"):
            required.append(param["name"])

    if operation.request_body_schema is not None:
        body_properties = operation.request_body_schema.get("properties", {})
        properties.update(body_properties)
        required.extend(operation.request_body_schema.get("required", []))

    return {"type": "object", "properties": properties, "required": required}
