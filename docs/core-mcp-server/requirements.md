# Requirements: transparent-openapi-mcp - core server

## Context

An MCP server that maps one or more OpenAPI v3 specifications 1:1 onto
the MCP tool list, transparently, so that changes to a spec (new
operations, changed parameters) never require a change to the server
implementation itself.

First production use case: an existing OpenAPI v3 spec with ~150 POST
operations representing elementary test steps executed against a
JavaFX GUI via QFTest, running inside a Podman container.

## Lifecycle model

Model A - stdio transport. The MCP server binary is spawned as a
child process of a single Claude session (started automatically from
the local Claude MCP configuration, or manually via /mcp). Each
session gets its own server process, its own memory, and its own
config state. Processes do not share state with each other; if 10
people each run a session, there are 10 independent server processes.
No network listener, no concurrent-connection handling is required
inside the server itself - isolation is provided by the OS process
model, not by server logic.

## Requirement groups

Group prefixes, in requirement-priority order (general control first,
then deployment/invocation, then configuration, then startup-phase
behavior, then tool mapping, then request forwarding, then the tech
stack used to build the server itself, then how it's released/
published). New requirements are added to their matching group with
the next free number; new groups get a new short prefix appended to
this list.

- CTRL  - general server/process control
- DEPLOY - how the server process is packaged and invoked (Podman)
- CFG   - configuration model (what a "config" is, how configs are defined)
- BOOT  - startup-phase resolution (how a config gets selected/validated)
- TOOLS - OpenAPI-spec-to-MCP-tool mapping
- FWD   - request forwarding to the backend
- STACK - tech stack / development process for the server itself
- RELEASE - source repo location, PyPI packaging/publishing, CI release workflow

## CTRL - general server/process control

R-CTRL-001. The server runs as a single OS process spawned per client
    session via stdio transport. No network listener is opened by the
    server itself.

R-CTRL-002. Concurrent sessions on the same host never interfere with
    each other. This is guaranteed by OS-level process isolation
    (one process per session), not by server-internal logic.

## DEPLOY - packaging and invocation

R-DEPLOY-001. The server is packaged as a container image, built from
    a Dockerfile with an entrypoint.sh, and named/tagged
    transparent-openapi-mcp. The Dockerfile installs the
    transparent-openapi-mcp Python package (R-RELEASE-002) and the
    entrypoint runs it - the container is a runtime wrapper around the
    published package, not a separately maintained copy of the code.

R-DEPLOY-002. The local Claude MCP configuration invokes the server by
    running the container as the stdio subprocess (e.g. `podman run -i
    --rm -v <local-config-file>:<container-path>:ro,Z
    transparent-openapi-mcp`), so R-CTRL-001 is satisfied with Podman
    transparently in between - Claude Code only ever sees a single
    child process communicating over stdio. The pre-selected config /
    config-list-URL reference is provided to the container by mounting
    a local config file into the container at a fixed path (not baked
    into the image, not passed via env var).

R-DEPLOY-003. Following the standard project layout, the repo provides
    a reentrant podman_build.sh (builds the image) and a reentrant
    podman_run.sh (used for local/manual testing of the container
    outside of a Claude session).

R-DEPLOY-004. The container has outbound network access at runtime -
    it fetches the config list, the OpenAPI spec URLs, and reaches the
    selected backend target URLs, all over the network. No offline/
    restricted network mode is required.

## CFG - configuration model

R-CFG-001. A "config" is a named bundle of one or more spec entries.
    Each spec entry pairs exactly:
    - one OpenAPI spec source URL, with its own tool-name prefix
      (see R-TOOLS-003)
    - one backend target base URL that operations from that spec are
      forwarded to (see R-FWD-001)
    A config with multiple spec entries may therefore forward to
    multiple different backends, one per spec.

R-CFG-002. More than one named config MAY be defined and available for
    selection at any time (a config list).

R-CFG-003. The config list is defined in JSON, using the same syntax
    conventions as Claude Code's own MCP configuration (.mcp.json /
    ~/.claude.json mcpServers entries), so that a single config entry
    can be copied directly into, or referenced from, a local Claude
    MCP configuration.

R-CFG-004. The server loads the config list from a URL to a raw JSON
    file at startup (not a local file, not a CLI-provided path). The
    syntax of this list file is structurally the same as a single
    concrete config entry (R-CFG-001) - a list is a self-similar
    wrapper around one or more such entries.

R-CFG-005. Each OpenAPI spec source URL in a config MAY specify its
    own request timeout for backend calls made against operations
    from that spec (see R-FWD-002). Test steps forwarded through this
    server can legitimately run for minutes (e.g. waiting for a batch
    job to finish), so no single fixed/global timeout is imposed.

R-CFG-006. A config (R-CFG-001) MAY specify its own default timeout,
    used for any of its spec URL entries that omit R-CFG-005.

R-CFG-007. The overall config list (R-CFG-004) MUST specify a
    server-wide default timeout. This is a mandatory field - there is
    no hardcoded last-resort value. Requiring it explicitly makes the
    expected duration of forwarded requests a visible, deliberate
    choice rather than an implicit assumption. A config list missing
    this field fails validation (R-BOOT-004/R-BOOT-005).

## BOOT - startup-phase resolution

R-BOOT-001. On process start, the server checks whether the invoking
    local Claude MCP configuration pre-selects a config by name.

R-BOOT-002. If a config is pre-selected, the server validates it
    (R-BOOT-004) and, on success, builds the tool list (R-TOOLS-001)
    before accepting any tool-call request.

R-BOOT-003. If no config is pre-selected, the server starts in an
    unconfigured state, exposing only the listConfig and selectConfig
    tools until a valid config is chosen.

R-BOOT-004. Selecting a config - whether pre-selected at startup or
    chosen at runtime via selectConfig - validates every URL it
    references (all spec URLs and all backend URLs) before any
    OpenAPI-derived tools are generated.

R-BOOT-005. If validation fails, the server reports the failure as
    clear, human/agent-readable text in the session, explicitly marked
    as an MCP config load error of this server (not a generic error).
    The report MUST:
      - name which URL(s) failed and why (e.g. unreachable, invalid
        JSON, schema mismatch)
      - state which local config file/location the user (or an agent
        acting on their behalf) needs to edit to correct it
      - give concrete guidance on what a valid value looks like, so
        the correction can be made without further back-and-forth
    The server remains in (or returns to) the unconfigured state
    described in R-BOOT-003 until a corrected config is selected.

## TOOLS - OpenAPI-spec-to-MCP-tool mapping

R-TOOLS-001. The server generates one MCP tool per OpenAPI operation
    found in the currently selected config's loaded spec(s), derived
    directly from each operation's schema (path, method, parameters,
    request body). No operation is hand-coded.

R-TOOLS-002. If a loaded OpenAPI spec changes and the config is
    reselected (or the process restarted), the resulting tool list
    reflects the change without any code change to the server. The
    mapping logic is generic and spec-driven.

R-TOOLS-003. Each spec source's operations are namespaced in the tool
    list using that spec's configured prefix (from R-CFG-001), e.g.
    <prefix>_<operationId>, avoiding collisions between multiple specs
    in the same config.

## FWD - request forwarding

R-FWD-001. When an OpenAPI-derived tool is called, the server forwards
    the call as an HTTP request to the backend base URL paired with
    that tool's source spec entry (R-CFG-001), using the path/method/
    params/body defined by that operation in its source spec, and
    returns the backend's response back through MCP.

R-FWD-002. The server applies a request timeout when forwarding a
    call, resolved in this order: the spec URL entry's own timeout
    (R-CFG-005), else the config's default timeout (R-CFG-006), else
    the server-wide default timeout (R-CFG-007).

## STACK - tech stack / development process

R-STACK-001. The server is implemented in Python, using the official
    MCP Python SDK for the stdio transport and tool-list protocol
    handling.

R-STACK-002. Development follows the standing 5 coding rules: no code
    without requirements, approved plan before implementation,
    test-driven development, testability as an architectural
    constraint, no "done" without tests.

R-STACK-003. The standing security CI gates apply to this stack:
    ShellCheck for entrypoint.sh/podman_build.sh/podman_run.sh,
    semgrep/bandit as Python SAST, and Trivy/Grype for the built
    container image. All are hard gates.

R-STACK-004. The project uses uv for dependency management and
    packaging, and pytest as the test framework, per the existing
    default Python stack.

R-STACK-005. The project targets the newest stable Python release
    line (currently 3.14.x - confirm exact patch version at
    implementation time, since patch releases ship regularly). Not
    an older LTS-style version.

## RELEASE - source repo, PyPI packaging, CI release workflow

R-RELEASE-001. The project's source of truth lives at
    github.com/roebi/transparent-openapi-mcp (public GitHub repo,
    matching this local git history).

R-RELEASE-002. The project builds and publishes a Python package
    named transparent-openapi-mcp to public PyPI, matching the
    existing pattern used by Roebi's other packages (e.g.
    skill-openapi-bridge, apiup).

R-RELEASE-003. Source code lives in a standard Python package folder
    layout (src/transparent_openapi_mcp/), matching R-STACK-004's
    tooling (uv build/publish).

R-RELEASE-004. Publishing follows the standing tag convention: a
    vX.Y.Z software version tag (distinct from the session-lifecycle
    handover/vN tag namespace) triggers a GitHub Actions workflow that
    builds and publishes the package to PyPI.

## Explicit non-goals (v1)

- No HTTP/SSE transport in v1 (Model B, shared multi-session server,
  is deferred - superseded by the Model A decision above).
- No authentication/authorization mechanism in v1. Current known
  backend (tide-openapi) requires none - trusted internal network.
  Revisit if a future backend requires credentials.
- No caching or hot-reload of specs while a config is active - specs
  are (re-)loaded only when a config is (re-)selected.

## Open questions for architecture phase

None remaining - all open questions from the requirements phase are
resolved as of this revision.
