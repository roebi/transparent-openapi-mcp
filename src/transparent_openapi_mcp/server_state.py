"""Testable core server logic - the BOOT sequence, config selection,
and tool dispatch, kept separate from the MCP SDK protocol wiring
(server.py is the thin adapter that connects this to stdio).

Covers:
  R-BOOT-001..005 - boot(): loads the config list, attempts the
    preselected config if any, returns a report string on failure.
  R-CFG-* / R-TOOLS-* - select_config(): validates and activates a
    named config, building its tool list.
  R-BOOT-003 - list_tools()/call_tool() only expose listConfig and
    selectConfig while unconfigured.
  R-FWD-001/002 - call_tool() forwards OpenAPI-derived tool calls via
    forwarder.forward_call(), applying the resolved timeout.
"""
from __future__ import annotations

from typing import Any

import httpx
from mcp.types import Tool

from transparent_openapi_mcp.config_loader import load_config_list
from transparent_openapi_mcp.config_model import Config, ConfigList, SpecEntry
from transparent_openapi_mcp.errors import format_config_load_error
from transparent_openapi_mcp.forwarder import forward_call
from transparent_openapi_mcp.openapi_parser import Operation, fetch_operations
from transparent_openapi_mcp.tool_builder import build_tools
from transparent_openapi_mcp.validator import validate_config

LIST_CONFIG_TOOL = Tool(
    name="listConfig",
    description="List the names of available backend configurations.",
    inputSchema={"type": "object", "properties": {}, "required": []},
)

SELECT_CONFIG_TOOL = Tool(
    name="selectConfig",
    description="Select which backend configuration this session's tool calls are routed against.",
    inputSchema={
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    },
)


class ServerNotConfiguredError(Exception):
    """Raised when an OpenAPI-derived tool is called before a config
    has been selected (R-BOOT-003)."""


class ToolExecutionError(Exception):
    """Raised for any other tool-call failure (unknown tool name, a
    selectConfig validation failure carrying the R-BOOT-005 report,
    etc). The message is meant to be surfaced to the caller as-is."""


class ServerState:
    """Process-local state for one MCP session (Model A: one process
    per session, so no per-session keying is needed - see R-CTRL-001/
    002)."""

    def __init__(self, client: httpx.AsyncClient, config_list_url: str):
        self._client = client
        self._config_list_url = config_list_url
        self._config_list: ConfigList | None = None
        self._selected_config: Config | None = None
        self._derived_tools: list[Tool] = []
        self._tool_index: dict[str, tuple[Operation, SpecEntry]] = {}

    def is_configured(self) -> bool:
        return self._selected_config is not None

    async def boot(self) -> str | None:
        """R-BOOT-001..003: load the config list; if a config is
        preselected, attempt to activate it. Returns the R-BOOT-005
        failure report string if activation fails, else None."""
        self._config_list = await load_config_list(self._client, self._config_list_url)
        if self._config_list.preselected is not None:
            try:
                await self._select_config(self._config_list.preselected)
            except ToolExecutionError as exc:
                return str(exc)
        return None

    def list_configs(self) -> list[str]:
        if self._config_list is None:
            return []
        return [config.name for config in self._config_list.configs]

    def list_tools(self) -> list[Tool]:
        control_tools = [LIST_CONFIG_TOOL, SELECT_CONFIG_TOOL]
        if not self.is_configured():
            return control_tools
        return control_tools + self._derived_tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name == "listConfig":
            return self.list_configs()
        if name == "selectConfig":
            config_name = arguments["name"]
            await self._select_config(config_name)
            return f'Config "{config_name}" selected.'

        if not self.is_configured():
            raise ServerNotConfiguredError(
                "No backend configuration is selected yet. Call listConfig "
                "to see available configs, then selectConfig to choose one."
            )

        tool_entry = self._tool_index.get(name)
        if tool_entry is None:
            raise ToolExecutionError(f'unknown tool "{name}"')
        operation, spec_entry = tool_entry
        assert self._config_list is not None  # is_configured() implies this
        timeout_seconds = self._config_list.effective_timeout_seconds(spec_entry)
        response = await forward_call(
            self._client,
            operation=operation,
            entry=spec_entry,
            timeout_seconds=timeout_seconds,
            arguments=arguments,
        )
        return response.json()

    async def _select_config(self, name: str) -> None:
        """R-BOOT-004/005: validate every URL in the named config;
        on success, activate it (build its tool list); on failure,
        raise ToolExecutionError carrying the failure report."""
        if self._config_list is None:
            self._config_list = await load_config_list(self._client, self._config_list_url)

        config = self._find_config(name)
        if config is None:
            available = ", ".join(self.list_configs()) or "(none)"
            raise ToolExecutionError(
                f'unknown config "{name}" - available configs: {available}'
            )

        failures = await validate_config(self._client, config)
        if failures:
            raise ToolExecutionError(
                format_config_load_error(
                    config_name=name,
                    failures=failures,
                    config_list_url=self._config_list_url,
                )
            )

        await self._activate_config(config)

    async def _activate_config(self, config: Config) -> None:
        derived_tools: list[Tool] = []
        tool_index: dict[str, tuple[Operation, SpecEntry]] = {}
        for entry in config.specs:
            operations = await fetch_operations(self._client, entry.spec_url)
            tools = build_tools(operations, prefix=entry.prefix)
            derived_tools.extend(tools)
            for operation, tool in zip(operations, tools):
                tool_index[tool.name] = (operation, entry)

        self._selected_config = config
        self._derived_tools = derived_tools
        self._tool_index = tool_index

    def _find_config(self, name: str) -> Config | None:
        if self._config_list is None:
            return None
        for config in self._config_list.configs:
            if config.name == name:
                return config
        return None
