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

## Configuration

Three separate files are involved - it's easy to miss one:

1. **The local config file** - mounted into the container (see
   `-v ...:/etc/transparent-openapi-mcp/config.json:ro,Z` in
   `podman_run.sh`). Contains only two fields:

   ```json
   {
     "configListUrl": "http://example/config-list.json",
     "preselected": "my-config-name"
   }
   ```

   `preselected` is optional - if omitted, the server starts
   unconfigured and only `listConfig`/`selectConfig` are available
   until a client calls `selectConfig`.

2. **The config list** - fetched *from* `configListUrl` at startup
   (must be reachable over HTTP, not a local file). Defines the named
   configs, each with one or more spec entries. `defaultTimeoutSeconds`
   at the top level is mandatory (no hardcoded fallback):

   ```json
   {
     "defaultTimeoutSeconds": 30,
     "configs": [
       {
         "name": "my-config-name",
         "specs": [
           {
             "prefix": "min",
             "specUrl": "http://example/my-openapi-spec.json",
             "backendBaseUrl": "http://example:8080"
           }
         ]
       }
     ]
   }
   ```

   `prefix` and `specUrl` are required; `backendBaseUrl` is required
   too - it's where calls to that spec's tools get forwarded.
   `timeoutSeconds` is optional per spec entry, falling back to a
   config-level `defaultTimeoutSeconds`, then the mandatory top-level
   one (see `src/transparent_openapi_mcp/config_model.py` for the
   full schema).

3. **The OpenAPI spec(s)** - referenced *from* a config entry's
   `specUrl`, also fetched over HTTP. Every operation **must** have
   an `operationId` - it's required to build the tool name.

### Tool naming

Every operation in a spec becomes one MCP tool named
`<prefix>_<operationId>`. Example: prefix `min` + `operationId:
"getRoot"` -> tool `min_getRoot`. This is how multiple spec sources
in one config avoid name collisions - give each a distinct prefix.

### Hostnames: container vs. direct

Whichever host names you put in `configListUrl` / `specUrl` /
`backendBaseUrl` must be reachable from wherever the server process
actually runs:

| Running as | Use |
|---|---|
| `podman run ...` (the container - normal use) | `host.containers.internal` to reach services on your host machine |
| `uv run python -m transparent_openapi_mcp` directly (no container) | `localhost` / `127.0.0.1` |

Mixing these up produces `ConnectError` / `Name or service not known`
- the two run modes have different network namespaces, so the same
hostname doesn't resolve the same way in both.

### Manual testing without Claude Code

`scripts/manual_mcp_client_test.py` drives the server as a real MCP
client over stdio - useful for checking a config end-to-end before
wiring it into Claude Code:

```sh
uv run python scripts/manual_mcp_client_test.py \
  --spawn "podman run -i --rm -v /path/to/local-config.json:/etc/transparent-openapi-mcp/config.json:ro,Z transparent-openapi-mcp:latest" \
  --call-tool <prefix>_<operationId>
```

See the script's own docstring for the direct (no-container) variant.
