# Next Steps - transparent-openapi-mcp

Instructions for you (Roebi) to take this from local git history to a
working, published MCP server. Everything the agent could do without
your credentials/access is done; everything below needs you.

## 1. Push to GitHub

The repo is meant to live at github.com/roebi/transparent-openapi-mcp
(R-RELEASE-001). Create that repo on GitHub (empty, no README/license
auto-init - this repo already has both), then:

```sh
cd transparent-openapi-mcp
git remote add origin git@github.com:roebi/transparent-openapi-mcp.git
git push origin main
git push origin 'refs/tags/handover/*'
```

Do NOT run `git push origin --tags` - it pushes both tag namespaces
at once and could trigger an unintended release later. Keep pushing
tag namespaces separately, even though no vX.Y.Z tag exists yet.

## 2. Set up PyPI trusted publishing

release.yml uses PyPI's trusted publishing (OIDC), not a stored API
token - no secret to create for PyPI itself. On pypi.org:

1. Create the project `transparent-openapi-mcp` on PyPI (or let the
   first trusted-publish create it - check current PyPI docs, this
   can vary).
2. Under the project's "Publishing" settings, add a trusted publisher:
   - Owner: roebi
   - Repository: transparent-openapi-mcp
   - Workflow: release.yml
   - Environment: release
3. In the GitHub repo settings, create an environment named `release`
   (Settings -> Environments -> New environment). This matches
   release.yml's `environment: release` and PyPI's trusted-publisher
   config above.

## 3. Add the semgrep secret

ci.yml's semgrep job reads `SEMGREP_APP_TOKEN`. If you have a
semgrep.dev account/token, add it under:
GitHub repo Settings -> Secrets and variables -> Actions -> New
repository secret, name `SEMGREP_APP_TOKEN`.

If you don't want a semgrep.dev account, tell the agent in a future
session and it can switch the semgrep job to a local/offline ruleset
instead (no token needed, slightly less coverage).

## 4. Test against your real environment

Nothing in this repo has been tested against the actual tide-openapi
spec or backend - every test uses a mocked HTTP transport. Before
trusting this in a real Claude Code session:

```sh
./podman_build.sh
```

Create a real local config file (copy local-config.example.json,
point configListUrl at wherever you host your actual config-list
JSON, matching the schema in
src/transparent_openapi_mcp/local_config.py and
src/transparent_openapi_mcp/config_model.py):

```sh
./podman_run.sh /path/to/your/real-config.json
```

This starts the container and waits on stdio - it will not print
anything by itself (that is correct MCP stdio behavior). To actually
exercise it, wire it into a Claude Code MCP config as described below,
or write a small manual MCP client script.

## 5. Wire it into Claude Code

In your Claude Code MCP config (per R-DEPLOY-002 - podman as the
stdio subprocess):

```json
{
  "mcpServers": {
    "transparent-openapi-mcp": {
      "command": "podman",
      "args": [
        "run", "-i", "--rm",
        "-v", "/path/to/your/real-config.json:/etc/transparent-openapi-mcp/config.json:ro",
        "transparent-openapi-mcp:latest"
      ]
    }
  }
}
```

Then in a Claude Code session, run `/mcp` and confirm
transparent-openapi-mcp shows up with its tools (listConfig,
selectConfig, plus every OpenAPI-derived tool once a config is
selected).

## 6. First real-world validation checklist

- [ ] Confirm your real OpenAPI spec parses without error (watch for
      $ref patterns not yet covered - openapi_parser.py handles local
      refs in request bodies, parameter schemas, and whole-parameter
      refs, including nested and circular refs, but not external refs
      to other files/URLs)
- [ ] Confirm tool names look right (prefix_operationId) and do not
      collide across multiple spec sources if you use more than one
- [ ] Call a known-safe test step through the MCP tool and confirm
      the response matches calling it directly against tide-openapi
- [ ] Try a deliberately invalid config (bad URL) via selectConfig and
      confirm the error report is clear enough to act on

## 7. First release

Once step 6 passes:

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
