# Claude Code MCP configuration

This is the *client-side* config - it tells Claude Code how to start
transparent-openapi-mcp as a stdio subprocess. Don't confuse it with
the server's own config (the local config / config list / OpenAPI
spec chain documented in [`../README.md`](../README.md)) - that's a
separate, unrelated piece.

## mcp-config.example.json

```json
{
  "mcpServers": {
    "transparent-openapi-mcp": {
      "command": "podman",
      "args": [
        "run", "-i", "--rm",
        "-v", "/absolute/path/to/t-o-m-config/local-config.json:/etc/transparent-openapi-mcp/config.json:ro,Z",
        "transparent-openapi-mcp:latest"
      ]
    }
  }
}
```

Replace `/absolute/path/to/t-o-m-config/local-config.json` with the
real path to *your* server-side local config file (see
[`../README.md`](../README.md) for what that file contains).

**Important:** this path must be absolute, and it is NOT
shell-expanded. Claude Code spawns `podman` directly as a subprocess
with this exact argument list - there's no shell in between to expand
`~` or environment variables. `~/t-o-m-config/local-config.json` will
not work; `/home/youruser/t-o-m-config/local-config.json` will.

## Where this goes

Merge the `mcpServers` entry above into your actual Claude Code MCP
configuration (project-level `.mcp.json`, or your user-level Claude
config, depending on how you use Claude Code) - don't just drop this
file in as-is if you already have other MCP servers configured, since
you'd overwrite them. Add the `"transparent-openapi-mcp": {...}` key
into your existing `mcpServers` object instead.

After saving, start (or reload) the MCP connection - in a Claude Code
session, run `/mcp` and confirm `transparent-openapi-mcp` shows up
with its tools (`listConfig`, `selectConfig`, plus every
OpenAPI-derived tool once a config is selected).
