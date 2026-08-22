#!/bin/sh
# Entrypoint (R-DEPLOY-001): runs the installed transparent-openapi-mcp
# package. No network listener is opened - the process communicates
# over stdio (R-CTRL-001).
set -eu

exec python -m transparent_openapi_mcp "$@"
