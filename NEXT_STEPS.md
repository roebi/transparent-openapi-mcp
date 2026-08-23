# Next Steps - transparent-openapi-mcp

## Status: v0.1.0 released

Published to [PyPI](https://pypi.org/project/transparent-openapi-mcp/)
on 2026-08-23. All setup/publish steps are done. What remains is
real-backend testing, which needs `tide-openapi` and isn't available
in this environment - see the use cases below for exactly what to run
when it is.

## Done

1. **Pushed to GitHub** - github.com/roebi/transparent-openapi-mcp
2. **PyPI trusted publishing** - configured and working (OIDC, no
   stored token); confirmed by the successful v0.1.0 publish
3. **Semgrep** - runs with public rulesets (`p/python`,
   `p/security-audit`), no account/token needed
4. **CI hardening** - Trivy container scan fixed (tarball scan
   instead of daemon lookup, `ignore-unfixed` policy), CVEs resolved
   (OS packages upgraded, stale bundled pip/setuptools/ensurepip
   bundle stripped from the image), GitHub Actions bumped to current
   versions (`checkout@v7`, `setup-uv` pinned)
5. **End-to-end validation with the bundled minimal example** - boot,
   `listConfig`/`selectConfig`, tool listing, and a real (non-mocked)
   tool call all confirmed working through the actual built
   container, using `scripts/manual_mcp_client_test.py`. Two real
   bugs were found and fixed this way (SELinux `:Z` mount flag,
   non-JSON backend response handling) - see CHANGELOG.md.
6. **First release** - `v0.1.0` tagged and published

## Still to do: wire into Claude Code

No Claude Code session was available in this environment. See
`examples/claude-code/README.md` for the exact config entry to add
when you do have one - it documents the config path requirement
(absolute, not shell-expanded) up front.

## Real-backend test use cases (run these once tide-openapi is reachable)

Each one is self-contained - run them in any order, using
`scripts/manual_mcp_client_test.py` the same way the minimal example
was tested, just pointing `specUrl`/`backendBaseUrl` at the real
tide-openapi spec and server instead of the bundled example.

### UC1 - Real spec parses cleanly

Point a config's `specUrl` at the actual tide-openapi.json. Call
`selectConfig`. Expect: no error, and `listConfig`/tool listing shows
roughly 150 tools named `<prefix>_<operationId>`. If it fails, the
error report should name which part of the spec failed - most likely
culprit is an unsupported `$ref` pattern (openapi_parser.py resolves
local refs including nested/circular, but not external file/URL
refs - see CHANGELOG.md "Added").

### UC2 - Multiple spec sources, no name collisions

Add a second spec entry to the same config (the bundled
`minimal-openapi.example.json` works fine as the second source) with
a distinct prefix. Call `selectConfig`, then list tools. Expect: both
sets of tools present, no name collisions (R-TOOLS-003).

### UC3 - Real tool call matches direct backend call

Pick one simple, safe, idempotent tide-openapi test step. Call it
through the MCP tool (`manual_mcp_client_test.py --call-tool
<prefix>_<operationId> --tool-args '{...}'`), and separately call the
same operation directly against tide-openapi (curl/Postman/whatever
you'd normally use). Expect: identical response body.

### UC4 - Backend error responses pass through cleanly

Call a real tide-openapi tool with an argument that the backend
itself will reject (not a client-side validation failure - something
tide-openapi's own logic rejects, e.g. a reference to a nonexistent
GUI element). Expect: the backend's actual error response comes back
through MCP as the tool result, not a Python traceback - this
exercises R-FWD-001's "return the backend's response" promise for the
error case, not just the success case (the happy-path version of this
was already confirmed with the minimal example).

### UC5 - Long-running test step respects its timeout

If tide-openapi has a batch-style step known to take multiple
minutes, set that spec entry's `timeoutSeconds` (or the config's
`defaultTimeoutSeconds`) generously and confirm the call completes
without being cut off. Then, optionally, set a deliberately too-short
timeout and confirm you get a clear timeout error rather than a hang
or a confusing failure.

## Still open / your decision

- No `$ref` support for external files/URLs (only local `#/...`
  refs) - flag it if your real spec needs that; it's a small addition
  once you know it's needed (see UC1).
