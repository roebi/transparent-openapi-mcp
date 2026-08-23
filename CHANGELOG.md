# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-23

### Added

- Initial release: a KISS MCP server that maps OpenAPI v3
  specifications 1:1 onto MCP tools, transparently to spec changes.
- `listConfig` and `selectConfig` MCP tools for choosing among named
  backend configurations at runtime, without editing files inside the
  running container.
- Support for multiple OpenAPI spec sources per config, each with its
  own tool-name prefix (`<prefix>_<operationId>`) to avoid collisions.
- Configurable per-request timeouts, resolved in order: per-spec
  entry, per-config default, mandatory server-wide default - so
  long-running test steps (e.g. waiting on a batch job) don't time
  out prematurely.
- Local (`#/...`) `$ref` resolution in OpenAPI parsing: request body
  schemas, parameter schemas, whole-parameter refs, nested refs
  inside `properties`/`items`/`allOf`/`anyOf`/`oneOf`, and safe
  handling of circular refs.
- Clear, actionable error reporting when a config fails validation
  (which URL failed, why, and how to fix it) instead of a raw
  stack trace.
- Podman-based containerized deployment: multi-stage `Dockerfile`,
  `entrypoint.sh`, `podman_build.sh`, `podman_run.sh`.
- `scripts/manual_mcp_client_test.py` - a standalone MCP client for
  exercising the server end-to-end without needing Claude Code.
- Configuration examples and documentation (`examples/`,
  `examples/claude-code/`) covering the full local-config -> config-
  list -> OpenAPI-spec chain and how to wire the server into Claude
  Code.
- CI pipeline: pytest, ShellCheck, bandit, semgrep (public rulesets,
  no account required), and a Trivy container vulnerability scan.
- GitHub Actions release workflow: a `vX.Y.Z` tag triggers build and
  publish to PyPI via trusted publishing (OIDC, no stored token).
- MIT license.

### Security

- Container image hardened against Trivy-flagged CVEs: OS packages
  upgraded to their patched versions at build time; the base image's
  stale bundled `pip`/`setuptools` (and Python's `ensurepip`
  bootstrap bundle, which carried its own separate, older copies)
  removed entirely, since neither has any runtime value once the
  package is installed.
- CI's Trivy gate fails on any vulnerability with an available fix;
  vulnerabilities with no upstream fix yet are not treated as
  blocking, since there is nothing actionable to do about them.

[Unreleased]: https://github.com/roebi/transparent-openapi-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/roebi/transparent-openapi-mcp/releases/tag/v0.1.0
