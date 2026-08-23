#!/usr/bin/env python3
"""Manual MCP client test - exercises the running server over stdio
without needing Claude Code.

Speaks the real MCP protocol via the official SDK's client module, so
this validates the same wire behavior a real MCP client would see:
listing tools, calling listConfig/selectConfig, and calling an
OpenAPI-derived tool and getting a real backend response back.

Usage (test the entrypoint directly, no container - fastest, good for
iterating on the code):

    uv run python scripts/manual_mcp_client_test.py \\
        --spawn "uv run python -m transparent_openapi_mcp" \\
        --env TRANSPARENT_OPENAPI_MCP_CONFIG=/path/to/local-config.json

Usage (test the actual built container - closer to production; no
--env needed, the config path is baked into the mount inside --spawn):

    uv run python scripts/manual_mcp_client_test.py \\
        --spawn "podman run -i --rm -v /path/to/local-config.json:/etc/transparent-openapi-mcp/config.json:ro,Z transparent-openapi-mcp:latest"

If your config's preselected entry is valid, this calls a tool named
<prefix>_<operationId> if you pass --call-tool <name> (optionally with
--tool-args '{"key": "value"}' as JSON).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shlex
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def run(command: str, args: list[str], env: dict[str, str], call_tool: str | None, tool_args: dict) -> None:
    server_params = StdioServerParameters(command=command, args=args, env=env)
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("initialized OK")

            tools_result = await session.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            print(f"tools ({len(tool_names)}): {tool_names}")

            list_config_result = await session.call_tool("listConfig", {})
            print("listConfig ->", [c.text for c in list_config_result.content])

            if call_tool is not None:
                result = await session.call_tool(call_tool, tool_args)
                status = "ERROR" if result.is_error else "OK"
                print(f"{call_tool} -> [{status}]", [c.text for c in result.content])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spawn", required=True, help="Full command to spawn, as one string (e.g. 'uv run python -m transparent_openapi_mcp')")
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Environment variable to pass to the spawned process (repeatable). "
        "The SDK spawns with a restricted default environment, not your shell's - "
        "pass TRANSPARENT_OPENAPI_MCP_CONFIG=... here if not using the default path.",
    )
    parser.add_argument("--call-tool", default=None, help="Tool name to call after listing (e.g. min_getRoot)")
    parser.add_argument("--tool-args", default="{}", help="JSON object of arguments for --call-tool")
    parsed = parser.parse_args()

    spawn_parts = shlex.split(parsed.spawn)
    if not spawn_parts:
        print("--spawn must not be empty", file=sys.stderr)
        sys.exit(1)
    command, args = spawn_parts[0], spawn_parts[1:]

    env: dict[str, str] = {}
    for item in parsed.env:
        if "=" not in item:
            print(f"--env value must be KEY=VALUE, got: {item}", file=sys.stderr)
            sys.exit(1)
        key, _, value = item.partition("=")
        env[key] = value

    try:
        tool_args = json.loads(parsed.tool_args)
    except json.JSONDecodeError as exc:
        print(f"--tool-args must be valid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(run(command, args, env, parsed.call_tool, tool_args))


if __name__ == "__main__":
    main()
