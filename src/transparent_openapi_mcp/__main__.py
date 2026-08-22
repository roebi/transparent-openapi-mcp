"""Entrypoint: starts the stdio MCP server (R-CTRL-001).

Reads the mounted local config file (R-DEPLOY-002), boots ServerState
against it, and runs the server over stdio. If the preselected config
fails validation at boot, the server still starts - it just stays in
the unconfigured state (R-BOOT-003) and the boot failure is logged to
stderr (stdout is reserved for the MCP protocol itself).
"""
from __future__ import annotations

import asyncio
import os
import sys

import httpx
from mcp.server.stdio import stdio_server

from transparent_openapi_mcp.local_config import load_local_config
from transparent_openapi_mcp.server import build_server
from transparent_openapi_mcp.server_state import ServerState

DEFAULT_LOCAL_CONFIG_PATH = "/etc/transparent-openapi-mcp/config.json"
LOCAL_CONFIG_PATH_ENV_VAR = "TRANSPARENT_OPENAPI_MCP_CONFIG"


async def async_main() -> None:
    local_config_path = os.environ.get(LOCAL_CONFIG_PATH_ENV_VAR, DEFAULT_LOCAL_CONFIG_PATH)
    local_config = load_local_config(local_config_path)

    async with httpx.AsyncClient() as client:
        state = ServerState(client, local_config.config_list_url)
        boot_error = await state.boot(preselected_override=local_config.preselected)
        if boot_error is not None:
            print(boot_error, file=sys.stderr)

        server = build_server(state)
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
