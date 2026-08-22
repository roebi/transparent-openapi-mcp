"""OpenAPI v3 spec fetching and operation extraction.

Feeds R-TOOLS-001: one MCP tool is generated per OpenAPI operation
found in a spec. This module is the pure-parsing half of that -
tool_builder.py turns the Operation objects produced here into MCP
Tool definitions.

Deliberately minimal: only the fields tool_builder.py and
forwarder.py need (path, method, operationId, parameters,
requestBody schema) are extracted. No OpenAPI features beyond what
the first production spec (~150 POST operations) uses are handled
yet - extend when a real spec needs more (e.g. $ref resolution).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass(frozen=True)
class Operation:
    """One OpenAPI operation (a path + HTTP method pair)."""

    operation_id: str
    path: str
    method: str
    summary: str | None = None
    parameters: list[dict[str, Any]] = field(default_factory=list)
    request_body_schema: dict[str, Any] | None = None


_HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


async def fetch_operations(client: httpx.AsyncClient, spec_url: str) -> list[Operation]:
    """Fetch spec_url and extract every operation from its paths.

    Every path+method pair whose value is an operation object (a key
    in _HTTP_METHODS) becomes one Operation. Extraction is a pure
    function of the spec content, so a changed spec yields a changed
    operation list with no code change (R-TOOLS-002).
    """
    response = await client.get(spec_url)
    response.raise_for_status()
    spec = response.json()
    return _extract_operations(spec)


def _extract_operations(spec: dict[str, Any]) -> list[Operation]:
    operations: list[Operation] = []
    for path, path_item in spec.get("paths", {}).items():
        for method, operation_obj in path_item.items():
            if method.lower() not in _HTTP_METHODS:
                continue
            operations.append(_build_operation(path, method, operation_obj))
    return operations


def _build_operation(path: str, method: str, operation_obj: dict[str, Any]) -> Operation:
    return Operation(
        operation_id=operation_obj["operationId"],
        path=path,
        method=method.lower(),
        summary=operation_obj.get("summary"),
        parameters=operation_obj.get("parameters", []),
        request_body_schema=_extract_request_body_schema(operation_obj),
    )


def _extract_request_body_schema(operation_obj: dict[str, Any]) -> dict[str, Any] | None:
    request_body = operation_obj.get("requestBody")
    if request_body is None:
        return None
    content = request_body.get("content", {})
    json_content = content.get("application/json")
    if json_content is None:
        return None
    return json_content.get("schema")
