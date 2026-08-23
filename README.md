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

## Configuration

See [`examples/README.md`](examples/README.md) for the full
configuration reference: the three-file chain (local config -> config
list -> OpenAPI spec), exact JSON schemas, the `<prefix>_<operationId>`
tool naming rule, container-vs-direct hostname rules, and a runnable
example set (`examples/*.json`) proven to work end-to-end.
