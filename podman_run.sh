#!/bin/sh
# Reentrant local/manual test run script (R-DEPLOY-003). Not used by
# Claude Code itself - Claude Code's MCP config invokes podman
# directly per R-DEPLOY-002. This script is for manually exercising
# the container outside of a session.
#
# Usage:
#   ./podman_run.sh /path/to/local-config.json
#
# local-config.json must match the LocalConfig schema
# (configListUrl, optional preselected) - see
# src/transparent_openapi_mcp/local_config.py.
set -eu

IMAGE_NAME="${IMAGE_NAME:-transparent-openapi-mcp}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
CONTAINER_CONFIG_PATH="${CONTAINER_CONFIG_PATH:-/etc/transparent-openapi-mcp/config.json}"

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /path/to/local-config.json" >&2
  exit 1
fi

LOCAL_CONFIG_FILE=$1

if [ ! -f "${LOCAL_CONFIG_FILE}" ]; then
  echo "Error: config file not found: ${LOCAL_CONFIG_FILE}" >&2
  exit 1
fi

podman run -i --rm \
  -v "${LOCAL_CONFIG_FILE}:${CONTAINER_CONFIG_PATH}:ro" \
  "${IMAGE_NAME}:${IMAGE_TAG}"
