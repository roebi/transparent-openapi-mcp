# Server Configuration Examples (Podman)

**This server is designed to run in a Podman container - that is the
only supported run mode.** Every hostname and every command below
assumes `podman run`; there is no direct/no-container mode documented
here, since running outside Podman was never the intended deployment
path.

Three files, matching a proven working setup (this exact combination
was tested end-to-end via `podman run`):

- `local-config.example.json`
- `config-list.example.json`
- `minimal-openapi.example.json`

All three already use `host.containers.internal`, Podman's DNS name
for reaching services on your host machine from inside the container.

## The Three Config Files and How They Link

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

## MCP Tool Naming: `<prefix>_<operationId>`

Every operation in a spec becomes one MCP tool named
`<prefix>_<operationId>`. In this example: prefix `min` +
`operationId: "getRoot"` -> tool `min_getRoot`. This is how multiple
spec sources in one config avoid name collisions - give each a
distinct prefix.

## Running the Bundled Example in Podman

### 1. Set up a config directory

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

### 2. Serve the config directory over HTTP

Leave this running in its own terminal:

```sh
cd ~/t-o-m-config
python3 -m http.server 8000
```

### 3. Build the image

From the repo root, in another terminal:

```sh
./podman_build.sh
```

### 4. Call a tool through the running container

`manual_mcp_client_test.py` spawns `podman` itself (via Python's
`shlex.split`, not a shell) - so unlike the `cd`/`mkdir` commands
above, `~` is **not** expanded here. Use the absolute path to your
`~/t-o-m-config` directory:

```sh
uv run python scripts/manual_mcp_client_test.py \
  --spawn "podman run -i --rm -v /absolute/path/to/t-o-m-config/local-config.json:/etc/transparent-openapi-mcp/config.json:ro,Z transparent-openapi-mcp:latest" \
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
