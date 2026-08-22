"""Config-list loading (R-CFG-004).

Fetches the config-list URL and parses it into a ConfigList. Reused
by both the BOOT sequence (config_loader step, see architecture.md)
and by validator.py callers that need a ConfigList to validate.
"""
from __future__ import annotations

import httpx
from pydantic import ValidationError

from transparent_openapi_mcp.config_model import ConfigList


class ConfigLoadError(Exception):
    """Raised when the config-list URL can't be fetched or parsed."""


async def load_config_list(client: httpx.AsyncClient, config_list_url: str) -> ConfigList:
    """Fetch config_list_url and parse it into a ConfigList.

    Raises ConfigLoadError with a human-readable reason on any
    failure: unreachable URL, non-2xx/3xx HTTP status, invalid JSON,
    or a JSON document that doesn't match the ConfigList schema
    (e.g. missing the mandatory defaultTimeoutSeconds, R-CFG-007).
    """
    try:
        response = await client.get(config_list_url)
    except httpx.RequestError as exc:
        raise ConfigLoadError(f"config-list URL unreachable ({exc})") from exc

    if response.status_code >= 400:
        raise ConfigLoadError(
            f"config-list URL returned HTTP {response.status_code}"
        )

    try:
        return ConfigList.model_validate_json(response.content)
    except ValidationError as exc:
        # A JSON parse failure and a schema mismatch both raise
        # pydantic's ValidationError here; give a clearer message for
        # the common case of genuinely invalid JSON.
        if _looks_like_invalid_json(response.content):
            raise ConfigLoadError(
                f"config-list content is invalid JSON ({exc})"
            ) from exc
        raise ConfigLoadError(
            f"config-list content does not match the expected schema ({exc})"
        ) from exc


def _looks_like_invalid_json(content: bytes) -> bool:
    import json

    try:
        json.loads(content)
    except (ValueError, TypeError):
        return True
    return False
