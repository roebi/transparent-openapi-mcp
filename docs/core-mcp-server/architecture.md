# Architecture: transparent-openapi-mcp - core server

Traces every design decision back to a requirement ID from
requirements.md. Anything not covered by a requirement is out of
scope for this revision.

## Component overview

Claude Code spawns `podman run -i --rm -v <config>:<path>:ro
transparent-openapi-mcp` as its single stdio child process (R-CTRL-001,
R-DEPLOY-001/002). Inside the container, one Python process runs the
MCP server, which owns three internal stages: a config loader/
validator, a tool builder, and a forwarder. See the component diagram
above for the shape of this pipeline.

## Module layout

```
transparent_openapi_mcp/
  __main__.py       entrypoint: starts the stdio MCP server
  server.py         MCP protocol glue: tool dispatch, listConfig/
                     selectConfig handlers, unconfigured-state guard
  config_model.py   pydantic models: SpecEntry, Config, ConfigList
  config_loader.py  fetches config-list URL, parses JSON into
                     ConfigList (R-CFG-004)
  validator.py      validates a Config's spec URLs + backend URLs are
                     reachable and well-formed (R-BOOT-004); builds
                     the structured failure report (R-BOOT-005)
  openapi_parser.py  fetches + parses an OpenAPI v3 spec, extracts
                     operations (path, method, parameters, requestBody)
  tool_builder.py    converts each operation into an MCP Tool
                     definition, applies the spec's prefix
                     (R-TOOLS-001/002/003)
  forwarder.py        builds and sends the HTTP request for a tool
                     call, resolves the timeout hierarchy
                     (R-FWD-001/002)
  errors.py          shared error types, incl. the BOOT-005 report
                     shape
```

Everything here reads from a single loaded Config (or none, in the
unconfigured state) held as process-local state - no per-session
bookkeeping is needed because R-CTRL-001/002 already guarantee one
process per session.

## Config data model (R-CFG-001 through R-CFG-007)

```
SpecEntry:
  prefix: str                 # tool name prefix, e.g. "tide"
  specUrl: str                 # URL to the OpenAPI v3 JSON
  backendBaseUrl: str          # paired backend base URL
  timeoutSeconds: int | null   # R-CFG-005, optional

Config:
  name: str
  specs: list[SpecEntry]        # one or more
  defaultTimeoutSeconds: int | null   # R-CFG-006, optional

ConfigList:
  configs: list[Config]
  defaultTimeoutSeconds: int    # R-CFG-007, MANDATORY
  preselected: str | null       # config name, matches R-BOOT-001
```

Example config-list JSON (R-CFG-003/004 - JSON, Claude-Code-config-like
shape, fetched from a URL, self-similar to a single Config entry):

```json
{
  "defaultTimeoutSeconds": 60,
  "preselected": "tide-openapi-prod",
  "configs": [
    {
      "name": "tide-openapi-prod",
      "defaultTimeoutSeconds": 300,
      "specs": [
        {
          "prefix": "tide",
          "specUrl": "https://internal.example/tide-openapi.json",
          "backendBaseUrl": "http://tide-openapi:8080",
          "timeoutSeconds": null
        }
      ]
    }
  ]
}
```

Timeout resolution for a call against an operation from this spec
entry (R-FWD-002): SpecEntry.timeoutSeconds (null here) -> Config.
defaultTimeoutSeconds (300s - long-running batch test steps) ->
ConfigList.defaultTimeoutSeconds (60s, never reached in this example).

## BOOT sequence (R-BOOT-001 through R-BOOT-005)

1. Process starts. The mounted config file (R-DEPLOY-002) is read -
   it contains the config-list URL and, optionally, a preselected
   config name (R-BOOT-001).
2. config_loader fetches and parses the config-list URL into a
   ConfigList (R-CFG-004).
3. If a config is preselected (R-BOOT-001): validator checks every
   spec URL and backend URL in that config (R-BOOT-004).
   - Success: tool_builder builds the tool list; server accepts
     tool-call requests (R-BOOT-002).
   - Failure: server enters the unconfigured state and returns the
     structured failure report (R-BOOT-005) on the next call.
4. If nothing is preselected: server starts directly in the
   unconfigured state, exposing only listConfig and selectConfig
   (R-BOOT-003).
5. selectConfig(name) at any time re-runs step 3 for the named
   config from the already-loaded ConfigList.

### R-BOOT-005 failure report shape

Returned as the tool result/error of selectConfig (or of the implicit
startup attempt, surfaced on the first tool call if it happened during
step 3):

```
MCP CONFIG LOAD ERROR (transparent-openapi-mcp)

Config "tide-openapi-prod" failed validation:
  - specUrl https://internal.example/tide-openapi.json: unreachable
    (connection refused)

To fix: edit the config-list file at <config-list URL> and correct
the failing entry above. A valid specUrl must point to a reachable
OpenAPI v3 JSON document; a valid backendBaseUrl must point to a
reachable HTTP endpoint. Re-run selectConfig("tide-openapi-prod")
after fixing.
```

## Tool generation (R-TOOLS-001/002/003)

For each SpecEntry in the selected Config:
1. openapi_parser fetches specUrl, parses the OpenAPI v3 JSON.
2. For every operation (path + method), tool_builder derives an MCP
   Tool: name = `<prefix>_<operationId>`, inputSchema built directly
   from the operation's parameters + requestBody JSON Schema.
3. No operation is special-cased - the mapping is a pure function of
   the spec, so re-running it against a changed spec yields a changed
   tool list with zero code changes (R-TOOLS-002).

## Request forwarding (R-FWD-001/002)

When `<prefix>_<operationId>` is called:
1. Look up the originating SpecEntry (backendBaseUrl + timeout chain).
2. Build the HTTP request: method/path from the operation, query/path
   params and request body from the tool-call arguments per the
   operation's schema.
3. Resolve timeout: SpecEntry -> Config -> ConfigList (mandatory).
4. Send the request to backendBaseUrl + path; return the response
   body back through MCP.

## Deployment (R-DEPLOY-001 through R-DEPLOY-004)

```
Dockerfile        builds from a pinned newest-stable Python 3.14.x
                   base image (R-STACK-005), installs deps via uv
                   (R-STACK-004), copies the package, sets
                   entrypoint.sh as ENTRYPOINT
entrypoint.sh      exec's `python -m transparent_openapi_mcp`
podman_build.sh    reentrant: podman build -t transparent-openapi-mcp .
podman_run.sh      reentrant: podman run -i --rm -v <local config>:
                   /etc/transparent-openapi-mcp/config.json:ro
                   transparent-openapi-mcp   (manual/local testing)
```

Network: default Podman bridge networking (outbound only) satisfies
R-DEPLOY-004 - no special network mode needed since the container only
makes outbound calls (config-list URL, spec URLs, backend URLs), never
listens for inbound connections (consistent with R-CTRL-001, no
network listener).

## Traceability

| Requirement group | Covered by |
|---|---|
| R-CTRL | Component overview, Module layout |
| R-DEPLOY | Deployment |
| R-CFG | Config data model |
| R-BOOT | BOOT sequence |
| R-TOOLS | Tool generation |
| R-FWD | Request forwarding |
| R-STACK | Deployment (Dockerfile), Module layout (Python/uv/pytest) |
| R-RELEASE | .github/workflows/release.yml (vX.Y.Z tag -> uv build + uv publish) |

## Open points for review

- Exact pydantic field validation rules (e.g. URL format checks) will
  be pinned down in the TDD phase per-module, not enumerated here.
- CI pipeline wiring for the R-STACK-003 security gates (ShellCheck/
  semgrep/bandit/Trivy) is a DEPLOY-adjacent detail to add once the
  repo has code to scan - not blocking this architecture.
