# Next Steps - transparent-openapi-mcp

Instructions for you (Roebi) to take this from local git history to a
working, published MCP server.

## 1. Push to GitHub - DONE

Pushed to github.com/roebi/transparent-openapi-mcp.

## 2. Set up PyPI trusted publishing - IN PROGRESS

Pending publisher registered on PyPI ("Registered a new pending
publisher to create the project"). Remaining: confirm the GitHub
`release` environment (created with defaults) matches what PyPI
expects, and that the first real release tag actually completes the
registration.

## 3. Semgrep - DONE (no account needed)

Switched ci.yml to a plain `semgrep scan` with public rulesets
(`p/python`, `p/security-audit`) - no `SEMGREP_APP_TOKEN`, no
semgrep.dev account required.

## 4. Test against your real environment - PARTIALLY DONE

Validated end-to-end with the bundled minimal example (see
`examples/README.md`) - both `podman_build.sh` and `podman_run.sh`
work, boot succeeds, `min_getRoot` was called through the container
via `scripts/manual_mcp_client_test.py` and returned a real (if
unremarkable) HTTP response. Two real bugs were found and fixed along
the way (SELinux `:Z` mount flag, non-JSON backend response
handling) - see commit history.

Still not done: testing against the actual tide-openapi spec and
backend (not available in this environment yet).

## 5. Wire it into Claude Code - NOT YET DONE

No Claude Code session available in this environment yet. See
`examples/claude-code/README.md` for the exact config entry to add
when you do have one available - it documents the config path
requirement (absolute, not shell-expanded) up front.

## 6. Real-world validation checklist

- [x] Tool names look right (`prefix_operationId`) - confirmed
      `min_getRoot` from the bundled example
- [x] Called a tool through the MCP protocol and got a real response
      back (not mocked) - confirmed via `manual_mcp_client_test.py`
      against both the direct entrypoint and the built container
- [ ] Confirm your real OpenAPI spec parses without error (watch for
      $ref patterns not yet covered - openapi_parser.py handles local
      refs in request bodies, parameter schemas, and whole-parameter
      refs, including nested and circular refs, but not external refs
      to other files/URLs)
- [ ] Confirm tool names do not collide across multiple spec sources
      if you use more than one (not yet tested - the bundled example
      only has one spec source)
- [ ] Call a known-safe *real* tide-openapi test step and confirm the
      response matches calling it directly
- [x] Try a deliberately invalid config (bad URL) via selectConfig and
      confirm the error report is clear enough to act on - verified:
      with no config preselected, only listConfig/selectConfig are
      exposed; selectConfig against an unreachable spec+backend
      returns a clear [ERROR] naming both failing URLs, which
      config-list file to fix, and how to re-run selectConfig once
      fixed; a subsequent selectConfig against the valid config in
      the same session succeeds normally

## 7. First release

Once step 6 passes (or once you're comfortable with what's verified
so far - the remaining unchecked items all need the real backend):

```sh
git tag v0.1.0
git push origin 'refs/tags/v*'
```

This triggers release.yml: tests run, then `uv build` + `uv publish`
publish to PyPI. Watch the Actions tab for the run.

## 8. Still open / your decision

- License is set to MIT (LICENSE file, pyproject.toml) - change this
  now if you want something else, before the first PyPI publish
  (changing license after a public release is messier).
- No $ref support for external files/URLs (only local #/... refs) -
  flag it if your spec needs that, it is a small addition.
