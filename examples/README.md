# Configuration examples

Three files, matching a proven working setup (this exact combination
was tested end-to-end - see `../scripts/manual_mcp_client_test.py`):

- `local-config.example.json`
- `config-list.example.json`
- `minimal-openapi.example.json`

## The three-file chain

It's easy to miss one of these - here's how they connect:

1. **The local config file** (`local-config.example.json`) - mounted
   into the container (see
   `-v ...:/etc/transparent-openapi-mcp/config.json:ro,Z` in
   `../podman_run.sh`). Contains only two fields:

   ```json
   {
     "configListUrl": "http://example/config-list.json",
     "preselected": "my-config-name"
   }
   ```

   `preselected` is optional - if omitted, the server starts
   unconfigured and only `listConfig`/`selectConfig` are available
   until a client calls `selectConfig`.

2. **The config list** (`config-list.example.json`) - fetched *from*
   `configListUrl` at startup (must be reachable over HTTP, not a
   local file). Defines the named configs, each with one or more spec
   entries. `defaultTimeoutSeconds` at the top level is mandatory (no
   hardcoded fallback):

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
   one (see `../src/transparent_openapi_mcp/config_model.py` for the
   full schema).

3. **The OpenAPI spec(s)** (`minimal-openapi.example.json`) -
   referenced *from* a config entry's `specUrl`, also fetched over
   HTTP. Every operation **must** have an `operationId` - it's
   required to build the tool name.

## Tool naming

Every operation in a spec becomes one MCP tool named
`<prefix>_<operationId>`. In this example: prefix `min` +
`operationId: "getRoot"` -> tool `min_getRoot`. This is how multiple
spec sources in one config avoid name collisions - give each a
distinct prefix.

## Hostnames: container vs. direct

Whichever host names you put in `configListUrl` / `specUrl` /
`backendBaseUrl` must be reachable from wherever the server process
actually runs. These example files use `host.containers.internal`,
which only resolves *inside* a running Podman container:

| Running as | Use |
|---|---|
| `podman run ...` (the container - normal use) | `host.containers.internal` to reach services on your host machine |
| `uv run python -m transparent_openapi_mcp` directly (no container) | `localhost` / `127.0.0.1` |

Mixing these up produces `ConnectError` / `Name or service not known`
- the two run modes have different network namespaces, so the same
hostname doesn't resolve the same way in both.

## Try it yourself

Serve this folder over HTTP:

```sh
cd examples
python3 -m http.server 8000
```

In another terminal, from the repo root:

```sh
./podman_build.sh
uv run python scripts/manual_mcp_client_test.py \
  --spawn "podman run -i --rm -v $(pwd)/examples/local-config.example.json:/etc/transparent-openapi-mcp/config.json:ro,Z transparent-openapi-mcp:latest" \
  --call-tool min_getRoot
```

Expect `tools (3): ['listConfig', 'selectConfig', 'min_getRoot']` and
a successful (if unremarkable) response from `min_getRoot` - the
Python http.server's own directory listing, since these examples
don't point at a real backend.

For your own real setup, copy these three files, replace the spec/
backend URLs with your real ones, and adjust hostnames per the table
above.
