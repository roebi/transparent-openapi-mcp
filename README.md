# transparent-openapi-mcp

A KISS MCP server that maps OpenAPI v3 specifications 1:1 onto MCP
tools, transparently - a change to a loaded OpenAPI spec never
requires a change to this server's own code.

See `docs/core-mcp-server/requirements.md` and
`docs/core-mcp-server/architecture.md` for the full requirement set
(R-CTRL, R-DEPLOY, R-CFG, R-BOOT, R-TOOLS, R-FWD, R-STACK, R-RELEASE)
and design.

## Quick start (local container test)

```sh
./podman_build.sh
./podman_run.sh local-config.example.json
```

`local-config.example.json` is a template - point `configListUrl` at
your own config-list URL before using it for real.
