"""MCP protocol glue.

Two layers, deliberately separated:

- handle_list_tools / handle_call_tool: pure async functions that
  take a ServerState and plain arguments, and return proper MCP
  result types (ListToolsResult-shaped list, CallToolResult). This is
  where the "wrap ServerState's outcome as an MCP result" logic lives,
  and it's fully unit-testable without touching the SDK's stdio
  transport or its context/params types.

- build_server: a thin adapter that wires those two functions into
  the SDK's Server(on_list_tools=..., on_call_tool=...) callback
  signatures (which carry a ServerRequestContext and SDK-specific
  params/result types). This layer has no logic of its own - it only
  translates between the SDK's calling convention and the functions
  above - so it is not unit-tested; correctness here is verified by
  running the server (see architecture.md's Open points for review).
"""
from __future__ import annotations

from typing import Any

from mcp import types
from mcp.server.lowlevel import Server

from transparent_openapi_mcp.server_state import (
    ServerNotConfiguredError,
    ServerState,
    ToolExecutionError,
)


async def handle_list_tools(state: ServerState) -> list[types.Tool]:
    return state.list_tools()


async def handle_call_tool(
    state: ServerState, name: str, arguments: dict[str, Any]
) -> types.CallToolResult:
    """Call state.call_tool() and wrap the outcome as a CallToolResult.

    Success: the result is serialized as text content, isError=False.
    ServerNotConfiguredError / ToolExecutionError (which carries the
    R-BOOT-005 report for a failed selectConfig, or any other
    dispatch failure): the message becomes the text content,
    isError=True, so the caller sees exactly what went wrong.
    """
    try:
        result = await state.call_tool(name, arguments)
    except (ServerNotConfiguredError, ToolExecutionError) as exc:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=str(exc))],
            isError=True,
        )
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=_as_text(result))],
        isError=False,
    )


def _as_text(result: Any) -> str:
    if isinstance(result, str):
        return result
    import json

    return json.dumps(result)


def build_server(state: ServerState) -> Server:
    """Wire handle_list_tools/handle_call_tool into the SDK's Server."""

    async def on_list_tools(_ctx: Any, _params: Any) -> types.ListToolsResult:
        return types.ListToolsResult(tools=await handle_list_tools(state))

    async def on_call_tool(_ctx: Any, params: types.CallToolRequestParams) -> types.CallToolResult:
        return await handle_call_tool(state, params.name, params.arguments or {})

    return Server(
        "transparent-openapi-mcp",
        on_list_tools=on_list_tools,
        on_call_tool=on_call_tool,
    )
