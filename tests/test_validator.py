"""Tests for transparent_openapi_mcp.validator.

Covers R-BOOT-004: every URL a config references (spec URLs and
backend URLs) is validated before any OpenAPI-derived tools are
generated. Uses httpx.MockTransport so no real network calls happen.
"""
import httpx
import pytest

from transparent_openapi_mcp.config_model import Config, SpecEntry
from transparent_openapi_mcp.validator import validate_config, validate_url_reachable


def _client_with_handler(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_validate_url_reachable_returns_none_on_success():
    def handler(request):
        return httpx.Response(200, json={"openapi": "3.0.0"})

    async with _client_with_handler(handler) as client:
        result = await validate_url_reachable(client, "https://x/spec.json")
    assert result is None


@pytest.mark.asyncio
async def test_validate_url_reachable_returns_failure_on_connect_error():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    async with _client_with_handler(handler) as client:
        result = await validate_url_reachable(client, "https://x/spec.json")
    assert result is not None
    assert result.url == "https://x/spec.json"
    assert "unreachable" in result.reason
    assert "connection refused" in result.reason


@pytest.mark.asyncio
async def test_validate_url_reachable_returns_failure_on_http_error_status():
    def handler(request):
        return httpx.Response(500)

    async with _client_with_handler(handler) as client:
        result = await validate_url_reachable(client, "https://x/spec.json")
    assert result is not None
    assert "unreachable" in result.reason
    assert "500" in result.reason


@pytest.mark.asyncio
async def test_validate_config_checks_every_spec_and_backend_url():
    def handler(request):
        return httpx.Response(200, json={"openapi": "3.0.0"})

    entry_a = SpecEntry(
        prefix="tide",
        spec_url="https://x/tide.json",
        backend_base_url="http://tide-backend:8080",
    )
    entry_b = SpecEntry(
        prefix="other",
        spec_url="https://x/other.json",
        backend_base_url="http://other-backend:8080",
    )
    config = Config(name="c", specs=[entry_a, entry_b])

    async with _client_with_handler(handler) as client:
        failures = await validate_config(client, config)
    assert failures == []


@pytest.mark.asyncio
async def test_validate_config_reports_failures_for_bad_urls():
    def handler(request):
        if "spec.json" in str(request.url):
            raise httpx.ConnectError("connection refused", request=request)
        return httpx.Response(200, json={"openapi": "3.0.0"})

    entry = SpecEntry(
        prefix="tide",
        spec_url="https://x/spec.json",
        backend_base_url="http://tide-backend:8080",
    )
    config = Config(name="c", specs=[entry])

    async with _client_with_handler(handler) as client:
        failures = await validate_config(client, config)
    assert len(failures) == 1
    assert failures[0].url == "https://x/spec.json"
    assert "unreachable" in failures[0].reason


@pytest.mark.asyncio
async def test_validate_config_reports_invalid_json_for_spec_url():
    def handler(request):
        if "spec.json" in str(request.url):
            return httpx.Response(200, content=b"not json")
        return httpx.Response(200, json={"openapi": "3.0.0"})

    entry = SpecEntry(
        prefix="tide",
        spec_url="https://x/spec.json",
        backend_base_url="http://tide-backend:8080",
    )
    config = Config(name="c", specs=[entry])

    async with _client_with_handler(handler) as client:
        failures = await validate_config(client, config)
    assert len(failures) == 1
    assert failures[0].url == "https://x/spec.json"
    assert "invalid JSON" in failures[0].reason
