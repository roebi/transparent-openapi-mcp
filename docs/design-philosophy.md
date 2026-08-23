# Design Philosophy

This document names the patterns underlying `transparent-openapi-mcp`'s
requirements. It does not introduce anything new - every claim here
cites the specific requirement ID(s) it is drawn from in
[`docs/core-mcp-server/requirements.md`](core-mcp-server/requirements.md).
Where this document and the requirements ever disagree, the
requirements are authoritative; this document should be corrected to
match, not the other way around.

## Transparency to change

The server has no knowledge of what any specific OpenAPI operation
*does* - only how to walk an operation's schema and turn it into an
MCP tool (R-TOOLS-001). Because the mapping is a pure function of the
spec content, a spec that gains, loses, or changes operations produces
a changed tool list with zero code changes to the server (R-TOOLS-002).
The same principle extends to deployment: the container is a thin
wrapper that installs and runs the published package rather than a
separately maintained copy of the source (R-DEPLOY-001), so there is
exactly one place the server's behavior is defined.

## Fail loud, name the fix

A config is validated - every spec URL and backend URL it references
- before any tool derived from it becomes callable (R-BOOT-004). On
failure, the server does not surface a generic error; it names which
URL failed, why, and where to make the correction (R-BOOT-005), and it
stays in an explicitly unconfigured state rather than a half-working
one (R-BOOT-003). The goal stated by these requirements is a
correction that does not require further back-and-forth.

## Explicit over implicit

Timeouts are resolved through a three-level fallback (per spec entry,
per config, per config list), and the outermost level is a mandatory
field with no hardcoded last-resort value (R-CFG-005 through
R-CFG-007, R-FWD-002). The stated reasoning is that a request's
expected duration should be a visible, deliberate choice rather than
an assumption baked into the code. The same instinct shows up in
R-CFG-003/004: the config-list format is deliberately self-similar to
a single config entry, rather than inventing a second, differently
shaped schema for the same kind of data.

## The deployment mechanism does not leak into the protocol contract

R-CTRL-001/002 specify one OS process per client session over stdio,
with isolation coming from the OS process model rather than
server-internal logic - the server does not need to know or care that
other sessions exist. R-DEPLOY-002 then wraps that same process in
Podman (`podman run -i --rm ...` as the spawned command) such that the
MCP client sees a single child process communicating over stdio,
identical to what it would see without the container. The
containerization is additive; it does not change the process model
the rest of the requirements were written against.

## Conventional tooling over novel tooling

R-STACK-001 uses the official MCP Python SDK rather than a hand-rolled
protocol implementation. R-STACK-004/005 use uv, pytest, and the
newest stable Python release line rather than a bespoke toolchain.
R-RELEASE-004 follows a standard `vX.Y.Z` tag -> CI-publish convention.
None of these decisions are specific to this project - each adopts an
existing, widely-used mechanism instead of building an equivalent one,
on the stated basis that this reduces what anyone (including a future
maintainer) has to learn to work on the project.
