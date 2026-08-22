"""Structured errors, including the R-BOOT-005 config-load failure
report.

R-BOOT-005 requires the report to:
  - be clearly marked as an MCP config load error of this server
  - name which URL(s) failed and why
  - state which config-list file/location to edit
  - give concrete guidance on what a valid value looks like
"""
from __future__ import annotations

from dataclasses import dataclass

SERVER_NAME = "transparent-openapi-mcp"


@dataclass(frozen=True)
class UrlFailure:
    """One URL that failed validation, and why."""

    url: str
    reason: str


def format_config_load_error(
    *,
    config_name: str,
    failures: list[UrlFailure],
    config_list_url: str,
) -> str:
    """Build the R-BOOT-005 report text.

    Matches the shape specified in architecture.md: a clearly marked
    header, the failing config name and each failed URL with its
    reason, and actionable guidance on where to fix it and what a
    valid value looks like.
    """
    failure_lines = "\n".join(f"  - {f.url}: {f.reason}" for f in failures)
    return (
        f"MCP CONFIG LOAD ERROR ({SERVER_NAME})\n"
        "\n"
        f'Config "{config_name}" failed validation:\n'
        f"{failure_lines}\n"
        "\n"
        f"To fix: edit the config-list file at {config_list_url} and "
        "correct the failing entry above. A valid specUrl must point "
        "to a reachable OpenAPI v3 JSON document; a valid "
        "backendBaseUrl must point to a reachable HTTP endpoint. "
        f'Re-run selectConfig("{config_name}") after fixing.'
    )
