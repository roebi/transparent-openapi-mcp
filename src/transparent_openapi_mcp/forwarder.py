"""Request forwarding to the backend (R-FWD-001, R-FWD-002).

Splits a tool call's arguments dict into path parameters, query
parameters, and request body fields according to the operation's
schema, builds the HTTP request against the paired backend base URL,
applies the resolved timeout, and returns the raw response so the
caller can pass it back through MCP unmodified.
"""
from __future__ import annotations

from typing import Any

import httpx

from transparent_openapi_mcp.config_model import SpecEntry
from transparent_openapi_mcp.openapi_parser import Operation


async def forward_call(
    client: httpx.AsyncClient,
    *,
    operation: Operation,
    entry: SpecEntry,
    timeout_seconds: float,
    arguments: dict[str, Any],
) -> httpx.Response:
    """Forward one tool call to entry.backend_base_url (R-FWD-001).

    arguments is the flat object MCP passes for a tool call - the
    same shape build_tool() advertised as the tool's input schema.
    This function un-flattens it back into path/query/body per the
    operation's parameter definitions.
    """
    path_params, query_params, body_fields = _split_arguments(operation, arguments)
    url = entry.backend_base_url.rstrip("/") + operation.path.format(**path_params)

    request_kwargs: dict[str, Any] = {
        "method": operation.method.upper(),
        "url": url,
        "timeout": timeout_seconds,
    }
    if query_params:
        request_kwargs["params"] = query_params
    if operation.request_body_schema is not None:
        request_kwargs["json"] = body_fields

    return await client.request(**request_kwargs)


def _split_arguments(
    operation: Operation, arguments: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    path_params: dict[str, Any] = {}
    query_params: dict[str, Any] = {}

    param_names_by_location: dict[str, str] = {}
    for param in operation.parameters:
        param_names_by_location[param["name"]] = param.get("in", "query")

    body_fields = dict(arguments)
    for name, location in param_names_by_location.items():
        if name not in arguments:
            continue
        value = body_fields.pop(name)
        if location == "path":
            path_params[name] = value
        else:
            query_params[name] = value

    if operation.request_body_schema is None:
        body_fields = {}

    return path_params, query_params, body_fields
