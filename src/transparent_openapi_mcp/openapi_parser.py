"""OpenAPI v3 spec fetching and operation extraction.

Feeds R-TOOLS-001: one MCP tool is generated per OpenAPI operation
found in a spec. This module is the pure-parsing half of that -
tool_builder.py turns the Operation objects produced here into MCP
Tool definitions.

Local ($ref: "#/...") references are resolved and inlined, since a
real-world spec commonly factors shared schemas/parameters into
components/*. Resolution covers: whole-parameter refs
(components/parameters/*), parameter/request-body schema refs
(components/schemas/*), and refs nested inside a schema's properties/
items/allOf/anyOf/oneOf. Circular refs are detected and left as an
unresolved {"$ref": ...} at the point of recursion, rather than
expanded infinitely - the resulting schema is still valid JSON Schema
(a $ref pointing back to itself), just not further inlined.

External ($ref to another file/URL) references are out of scope -
not needed for the first production spec.
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
            operations.append(_build_operation(spec, path, method, operation_obj))
    return operations


def _build_operation(spec: dict[str, Any], path: str, method: str, operation_obj: dict[str, Any]) -> Operation:
    return Operation(
        operation_id=operation_obj["operationId"],
        path=path,
        method=method.lower(),
        summary=operation_obj.get("summary"),
        parameters=_resolve_parameters(spec, operation_obj.get("parameters", [])),
        request_body_schema=_extract_request_body_schema(spec, operation_obj),
    )


def _resolve_parameters(spec: dict[str, Any], parameters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for param in parameters:
        if "$ref" in param:
            param = _resolve_ref(spec, param["$ref"])
        param = dict(param)
        if "schema" in param:
            param["schema"] = _resolve_schema(spec, param["schema"])
        resolved.append(param)
    return resolved


def _extract_request_body_schema(spec: dict[str, Any], operation_obj: dict[str, Any]) -> dict[str, Any] | None:
    request_body = operation_obj.get("requestBody")
    if request_body is None:
        return None
    content = request_body.get("content", {})
    json_content = content.get("application/json")
    if json_content is None:
        return None
    schema = json_content.get("schema")
    if schema is None:
        return None
    return _resolve_schema(spec, schema)


def _resolve_ref(spec: dict[str, Any], ref: str) -> dict[str, Any]:
    """Resolve a local JSON pointer ref like '#/components/schemas/X'."""
    if not ref.startswith("#/"):
        raise ValueError(f"only local refs are supported, got: {ref}")
    node: Any = spec
    for segment in ref[2:].split("/"):
        node = node[segment]
    return node


def _resolve_schema(
    spec: dict[str, Any], schema: dict[str, Any], seen_refs: frozenset[str] = frozenset()
) -> dict[str, Any]:
    """Recursively inline every local $ref within schema.

    seen_refs tracks the chain of refs currently being expanded, so a
    cycle (a ref that points back to one already being expanded)
    stops recursion and leaves that occurrence as an unresolved
    {"$ref": ...} instead of looping forever.
    """
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in seen_refs:
            return {"$ref": ref}
        target = _resolve_ref(spec, ref)
        return _resolve_schema(spec, target, seen_refs | {ref})

    resolved = dict(schema)

    if "properties" in resolved:
        resolved["properties"] = {
            name: _resolve_schema(spec, prop_schema, seen_refs)
            for name, prop_schema in resolved["properties"].items()
        }
    if "items" in resolved:
        resolved["items"] = _resolve_schema(spec, resolved["items"], seen_refs)
    for keyword in ("allOf", "anyOf", "oneOf"):
        if keyword in resolved:
            resolved[keyword] = [_resolve_schema(spec, sub, seen_refs) for sub in resolved[keyword]]

    return resolved
