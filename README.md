# transparent-openapi-mcp

A KISS MCP server that maps OpenAPI v3 specifications 1:1 onto MCP
tools, transparently - a change to a loaded OpenAPI spec never
requires a change to this server's own code.

## Using this as a Claude Code MCP server

Three steps: build the image, set up your server-side config, wire it
into Claude Code.

### 1. Build

```sh
./podman_build.sh
```

### 2. Configure the server

The server needs its own config: a local file (mounted into the
container) that points at a config list, which in turn points at your
OpenAPI spec(s) and backend(s). See
[`examples/README.md`](examples/README.md) for the full reference -
what each file contains, the `<prefix>_<operationId>` tool naming
rule, and a runnable example set proven to work end-to-end.

### 3. Wire it into Claude Code

Claude Code needs to know how to start the container as a stdio
subprocess. See
[`examples/claude-code/README.md`](examples/claude-code/README.md)
for the exact MCP config entry to add and how it relates to your
server-side config from step 2.

Once added, run `/mcp` in a Claude Code session and confirm
`transparent-openapi-mcp` shows up with its tools.

## Try it with the bundled example

Before wiring in your own real spec/backend, you can verify the whole
chain works using the bundled minimal example:

```sh
./podman_build.sh

mkdir -p ~/t-o-m-config
cp examples/*.example.json ~/t-o-m-config/
cd ~/t-o-m-config
mv local-config.example.json local-config.json
mv config-list.example.json config-list.json
mv minimal-openapi.example.json minimal-openapi.json

# in another terminal, serve that directory:
cd ~/t-o-m-config && python3 -m http.server 8000

# back in the first terminal:
./podman_run.sh ~/t-o-m-config/local-config.json
```

See [`examples/README.md`](examples/README.md#try-it-yourself) for
the full walkthrough, including how to actually call a tool and see
a result (this just starts the server - it sits silently on stdio,
which is correct MCP behavior).

## Design docs

See `docs/core-mcp-server/requirements.md` and
`docs/core-mcp-server/architecture.md` for the full requirement set
(R-CTRL, R-DEPLOY, R-CFG, R-BOOT, R-TOOLS, R-FWD, R-STACK, R-RELEASE)
and design.
