"""URL validation for the BOOT sequence (R-BOOT-004).

Every spec URL and backend URL referenced by a Config is checked
before any OpenAPI-derived tools are generated for it. Spec URLs are
additionally checked for parseable JSON, since a spec that can't be
parsed can't be mapped to tools (R-TOOLS-001).
"""
from __future__ import annotations

import httpx

from transparent_openapi_mcp.config_model import Config
from transparent_openapi_mcp.errors import UrlFailure


async def validate_url_reachable(client: httpx.AsyncClient, url: str) -> UrlFailure | None:
    """Check that a URL is reachable over HTTP.

    Returns None on success, or a UrlFailure describing why the URL
    is unreachable (connection error or a non-2xx/3xx HTTP status).
    """
    try:
        response = await client.get(url)
    except httpx.RequestError as exc:
        return UrlFailure(url=url, reason=f"unreachable ({exc})")
    if response.status_code >= 400:
        return UrlFailure(url=url, reason=f"unreachable (HTTP {response.status_code})")
    return None


async def _validate_spec_url(client: httpx.AsyncClient, url: str) -> UrlFailure | None:
    """Reachability plus JSON-parseability check for a spec URL."""
    try:
        response = await client.get(url)
    except httpx.RequestError as exc:
        return UrlFailure(url=url, reason=f"unreachable ({exc})")
    if response.status_code >= 400:
        return UrlFailure(url=url, reason=f"unreachable (HTTP {response.status_code})")
    try:
        response.json()
    except ValueError:
        return UrlFailure(url=url, reason="invalid JSON")
    return None


async def validate_config(client: httpx.AsyncClient, config: Config) -> list[UrlFailure]:
    """Validate every spec URL and backend URL in a config.

    Returns the list of failures found (empty list if everything is
    valid). Checks all entries rather than stopping at the first
    failure, so a single validation pass reports everything that
    needs fixing (R-BOOT-005).
    """
    failures: list[UrlFailure] = []
    for entry in config.specs:
        spec_failure = await _validate_spec_url(client, entry.spec_url)
        if spec_failure is not None:
            failures.append(spec_failure)
        backend_failure = await validate_url_reachable(client, entry.backend_base_url)
        if backend_failure is not None:
            failures.append(backend_failure)
    return failures
