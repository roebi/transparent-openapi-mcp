#!/bin/sh
# Reentrant build script (R-DEPLOY-003). Safe to run repeatedly -
# podman build rebuilds only changed layers.
set -eu

SCRIPT_DIR=$(dirname -- "$0")
SCRIPT_DIR=$(cd -- "${SCRIPT_DIR}" && pwd)
IMAGE_NAME="${IMAGE_NAME:-transparent-openapi-mcp}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

podman build \
  -t "${IMAGE_NAME}:${IMAGE_TAG}" \
  -f "${SCRIPT_DIR}/Dockerfile" \
  "${SCRIPT_DIR}"

echo "Built ${IMAGE_NAME}:${IMAGE_TAG}"
