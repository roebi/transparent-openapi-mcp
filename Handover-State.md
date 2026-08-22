# Handover State

## Project
transparent-openapi-mcp

## Status
Full v1 deliverable complete: core application (TDD, 69/69 tests),
containerization, CI/release workflows, MIT license, PyPI packaging
metadata. Ready for real-world testing against the actual tide
backend and the ~150-operation OpenAPI spec.

## What's built
- docs/core-mcp-server/requirements.md - R-CTRL, R-DEPLOY, R-CFG,
  R-BOOT, R-TOOLS, R-FWD, R-STACK, R-RELEASE (all resolved)
- docs/core-mcp-server/architecture.md - full traceability to
  requirements, including the CI/release workflow design
- src/transparent_openapi_mcp/: config_model, errors, validator,
  config_loader, openapi_parser, tool_builder, forwarder,
  local_config, server_state, server, __main__ - all TDD, 69 tests
  green (uv run pytest)
- Dockerfile (multi-stage, R-DEPLOY-001), entrypoint.sh,
  podman_build.sh, podman_run.sh - all ShellCheck-clean
- .github/workflows/ci.yml - pytest, ShellCheck, bandit, semgrep,
  Trivy container scan (R-STACK-003)
- .github/workflows/release.yml - vX.Y.Z tag -> uv build + uv publish
  to PyPI, handover/* tags excluded (R-RELEASE-004)
- LICENSE (MIT), pyproject.toml license/classifiers filled in
- local-config.example.json for manual/local podman_run.sh testing

## Known issues
None currently known. semgrep could not be run locally in the
sandboxed dev environment (semgrep.dev registry not reachable from
that network) - it is wired into CI where it will run with full
network access; not yet verified against a real GitHub Actions run.

## Deferred items
- Repo not yet pushed to github.com/roebi/transparent-openapi-mcp
  (still local-only git history)
- No real-world test yet against the actual tide-openapi backend or
  the ~150-operation production spec (all tests use
  httpx.MockTransport)
- PyPI publish not yet attempted (needs GitHub repo + PyPI trusted
  publishing setup + first vX.Y.Z tag)
- SEMGREP_APP_TOKEN secret not yet configured in the GitHub repo
  (referenced by ci.yml's semgrep job)

## Next steps
- Push to GitHub, set up PyPI trusted publishing
- Test against the real tide-openapi OpenAPI spec and backend
- First vX.Y.Z release tag once real-world testing passes
