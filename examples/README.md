# Configuration examples

Three files, matching a proven working setup (this exact combination
was tested end-to-end via `podman run`):

- `local-config.example.json`
- `config-list.example.json`
- `minimal-openapi.example.json`

**Primary run mode is the Podman container** - that's what
`podman_run.sh`, a real Claude Code MCP config, and these examples
are built around. All three files below already use
`host.containers.internal`, Podman's DNS name for reaching services
on your host machine from inside the container.

## The three-file chain

It's easy to miss one of these - here's how they connect:

1. **The local config file** (`local-config.example.json`) - mounted
   into the container (see
   `-v ...:/etc/transparent-openapi-mcp/config.json:ro,Z` in
   `../podman_run.sh`). Contains only two fields:

   ```json
   {
     "configListUrl": "http://host.containers.internal:8000/config-list.json",
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
             "specUrl": "http://host.containers.internal:8000/minimal-openapi.json",
             "backendBaseUrl": "http://host.containers.internal:8000"
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

## Try it yourself

Set up a working directory outside the repo - this mirrors a real
deployment, where your config lives separately from the source
checkout:

```sh
mkdir -p ~/t-o-m-config
cp examples/*.example.json ~/t-o-m-config/
cd ~/t-o-m-config
mv local-config.example.json local-config.json
mv config-list.example.json config-list.json
mv minimal-openapi.example.json minimal-openapi.json
```

Serve that directory over HTTP (leave this running in its own
terminal):

```sh
cd ~/t-o-m-config
python3 -m http.server 8000
```

Build the image (from the repo root, in another terminal):

```sh
./podman_build.sh
```

Call a tool through the running container:

```sh
uv run python scripts/manual_mcp_client_test.py \
  --spawn "podman run -i --rm -v ~/t-o-m-config/local-config.json:/etc/transparent-openapi-mcp/config.json:ro,Z transparent-openapi-mcp:latest" \
  --call-tool min_getRoot
```

Expect `tools (3): ['listConfig', 'selectConfig', 'min_getRoot']` and
a successful (if unremarkable) response from `min_getRoot` - the
Python http.server's own directory listing, since these examples
don't point at a real backend.

For your own real setup: edit the three files in `~/t-o-m-config`
(or wherever you keep them) with your real spec/backend URLs, keeping
`host.containers.internal` for anything that needs to reach your host
machine from inside the container.

## Running directly without a container (not the primary mode)

For quick local iteration on the code itself, you can skip Podman
entirely and run the entrypoint directly - but then `localhost` /
`127.0.0.1` replaces `host.containers.internal` everywhere in your
config files, since there's no container network namespace involved:

```sh
TRANSPARENT_OPENAPI_MCP_CONFIG=~/t-o-m-config/local-config.json \
  uv run python -m transparent_openapi_mcp
```

Mixing the two hostname conventions up produces `ConnectError` /
`Name or service not known` - keep a container-mode and a direct-mode
copy of your config files if you need both.
