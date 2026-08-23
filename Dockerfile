# syntax=docker/dockerfile:1
#
# Multi-stage build (R-DEPLOY-001): the builder stage builds the
# transparent-openapi-mcp wheel from source using uv, the same
# packaging path used for the PyPI release (R-RELEASE-002). The
# runtime stage installs only that wheel - the container is a
# runtime wrapper around the package, not a separately maintained
# copy of the source (R-DEPLOY-001).
#
# Base image pinned to the newest stable Python release line
# (R-STACK-005). Confirm the exact patch tag is current at build
# time - see requirements.md R-STACK-005.

FROM python:3.14-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /build
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ src/

RUN uv build --wheel --out-dir /build/dist

FROM python:3.14-slim AS runtime

# Pull already-patched OS packages - the base image snapshot lags
# Debian's own security repo by some margin (Trivy CVE scan, R-STACK-003).
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /usr/sbin/nologin mcp

# The base image's bundled pip/setuptools are also stale (Trivy
# flags known CVEs in both) - upgrade before installing our wheel.
RUN pip install --no-cache-dir --upgrade pip setuptools

COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -rf /tmp/*.whl

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

USER mcp

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
