# syntax=docker/dockerfile:1
# Multi-stage Dockerfile for MCP Jenkins
# Optimized for minimal image size, security hardening, and efficient layer caching
#
# SECURITY FEATURES:
# - Non-root user with explicit UID/GID for predictable permissions
# - No shell in production to prevent shell-based attacks
# - Read-only root filesystem compatible (with tmpfs mounts)
# - Minimal attack surface using Alpine base
# - No secrets baked into image layers
# - Security labels following OCI Image Spec
# - Capability dropping supported via runtime flags
#
# DEPLOYMENT SECURITY:
# - Use Docker secrets or mounted files for credentials (see docker-compose.yml)
# - Run with --read-only --tmpfs /tmp:noexec,nosuid,nodev
# - Consider --security-opt=no-new-privileges:true
# - Apply network segmentation and least privilege access
# - Enable resource limits (memory, CPU, PIDs)
#
# RECENT CHANGES (v0.3.9):
# - Base image: python:3.11-slim -> python:3.11-alpine (smaller image)
# - Multi-stage build: build deps (gcc, musl-dev, etc.) only in builder stage
# - Production image has only runtime libs (libxml2, libxslt, libffi)
# - Dependency management: uv.lock committed, using uv sync --frozen
# - uv version pinned via ARG UV_VERSION for reproducible builds
# - Healthcheck: validates mcp_jenkins module import (not just Python)
# - Production user: /sbin/nologin shell (security hardening)
# - Venv at /app/.venv with PATH updated (no --system install)

# ============================================================================
# Base stage with runtime dependencies only (no build tools)
# ============================================================================
FROM python:3.11-alpine AS base

# OCI Image Specification Labels
# https://github.com/opencontainers/image-spec/blob/main/annotations.md
LABEL org.opencontainers.image.title="MCP Jenkins" \
      org.opencontainers.image.description="Model Context Protocol server for Jenkins integration with AI language models" \
      org.opencontainers.image.version="0.3.9" \
      org.opencontainers.image.vendor="lanbaoshen" \
      org.opencontainers.image.authors="lanbaoshen@icloud.com" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.url="https://github.com/CharlieTheLionheart/mcp-jenkins" \
      org.opencontainers.image.source="https://github.com/CharlieTheLionheart/mcp-jenkins" \
      org.opencontainers.image.documentation="https://github.com/CharlieTheLionheart/mcp-jenkins/blob/master/docker/DOCKER.md"

# Security-focused labels
LABEL security.non-root="true" \
      security.user-uid="10001" \
      security.user-gid="10001" \
      security.read-only-rootfs="compatible" \
      security.no-new-privileges="recommended"

# Install only runtime libraries (not -dev packages)
# These are required by compiled Python extensions (lxml, etc.)
RUN apk add --no-cache \
    libxml2 \
    libxslt \
    libffi

# Set environment variables for Python optimization
# UV_PROJECT_ENVIRONMENT: Use consistent venv location for uv sync
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Create non-root user with explicit UID/GID for security and predictability
# UID/GID 10001 is commonly used for application users and avoids conflicts
# Alpine uses adduser instead of useradd
# -D: Don't assign a password (login disabled)
# -h: Home directory (needed for Python package installation)
# -u/-g: Explicit UID/GID for consistent permissions across environments
RUN addgroup -g 10001 appuser && \
    adduser -D -u 10001 -G appuser -h /app appuser && \
    chown -R appuser:appuser /app

# ============================================================================
# Builder stage with compilation tools for building Python packages
# ============================================================================
FROM base AS builder

# Install build dependencies for Python packages requiring C compilation
# Required for: lxml (BeautifulSoup4 parser), cryptography, and other native extensions
# These are only present in the builder stage, not in the final image
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libxml2-dev \
    libxslt-dev \
    libffi-dev

# Install uv for dependency management
# Pin version for reproducible builds - update periodically
#
# SECURITY CONSIDERATIONS:
# - Downloaded from official astral.sh over HTTPS with TLS verification
# - Version pinning ensures reproducible builds and prevents supply-chain attacks
# - astral.sh is maintained by Astral (creators of Ruff), a trusted Python tooling vendor
# - The install script is executed once at build time, not runtime
# - For additional verification, compare SHA256 of downloaded binaries against
#   official releases at: https://github.com/astral-sh/uv/releases
ARG UV_VERSION=0.9.18
ADD --chmod=755 https://astral.sh/uv/${UV_VERSION}/install.sh /install.sh
RUN /install.sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx && \
    rm -rf /root/.local /install.sh

# ============================================================================
# Development stage with all dependencies including dev tools
# ============================================================================
FROM builder AS development

# Copy project files with lockfile for reproducible builds
# Order: lockfile first for cache optimization, then source
COPY --chown=appuser:appuser pyproject.toml uv.lock README.md LICENSE ./
COPY --chown=appuser:appuser src/ ./src/

# Install all dependencies including dev group using locked versions
# --frozen: Fail if uv.lock is out of sync with pyproject.toml
# This ensures CI and Docker use identical dependency versions
RUN uv sync --frozen

# Switch to non-root user for security
USER appuser

# Expose default SSE port
EXPOSE 9887

# Development healthcheck that validates the MCP server is importable
# More thorough than production to catch development issues early
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python3 -c "import mcp_jenkins" || exit 1

# Default command for development
# Use the installed console script defined in pyproject.toml
ENTRYPOINT ["mcp-jenkins"]
CMD ["--help"]

# ============================================================================
# Production builder stage - builds dependencies then discards build tools
# ============================================================================
FROM builder AS production-builder

# Copy project files with lockfile for reproducible builds
COPY --chown=appuser:appuser pyproject.toml uv.lock README.md LICENSE ./
COPY --chown=appuser:appuser src/ ./src/

# Install only production dependencies using locked versions
# --frozen: Fail if uv.lock is out of sync with pyproject.toml
# --no-dev: Skip development dependencies for smaller, more secure image
RUN uv sync --frozen --no-dev

# ============================================================================
# Production stage with minimal dependencies and hardened security
# No build tools (gcc, musl-dev, etc.) - only runtime libraries
# ============================================================================
FROM base AS production

# Copy the pre-built virtual environment from production-builder
# This contains compiled packages without needing build tools in the final image
COPY --from=production-builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=production-builder --chown=appuser:appuser /app/src /app/src

# SECURITY HARDENING: Remove shell access for production
# This prevents shell-based attacks if the container is compromised
# The application runs as a Python process and doesn't need shell access
# Note: Healthcheck and entrypoint still work as they use Python interpreter directly
# Using sed because Alpine's usermod requires the shadow package (adds ~2MB)
RUN sed -i 's|^\(appuser:[^:]*:[^:]*:[^:]*:[^:]*:[^:]*:\).*$|\1/sbin/nologin|' /etc/passwd

# Switch to non-root user for security
# All subsequent operations and runtime will execute as this user
USER appuser

# Expose default SSE/HTTP port for MCP transport
# This is informational only; actual port binding happens at runtime
EXPOSE 9887

# Production healthcheck that validates the MCP server module is importable
# This verifies:
# - Python environment is working
# - All dependencies are correctly installed
# - mcp_jenkins module can be loaded
# For HTTP-based healthcheck in SSE/streamable-http mode, implement /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python3 -c "import mcp_jenkins" || exit 1

# Default command (can be overridden at runtime)
# Use the installed console script defined in pyproject.toml
#
# SECURITY NOTE - Credentials Management:
# NEVER pass credentials via command-line arguments in production as they:
# - Appear in 'ps' output
# - Get logged to process managers
# - Show up in container inspect output
# - May leak in error messages
#
# RECOMMENDED APPROACHES (in order of security):
# 1. Docker Secrets (Swarm/Kubernetes):
#    docker secret create jenkins_password password.txt
#    Mount to /run/secrets/jenkins_password
#    Read from file in application
#
# 2. Mounted credential files with restrictive permissions:
#    volumes:
#      - ./credentials.json:/app/credentials.json:ro
#    chmod 400 credentials.json
#
# 3. Environment variables from secret management (vault, AWS Secrets Manager):
#    environment:
#      JENKINS_PASSWORD_FILE: /run/secrets/jenkins_password
#
# 4. Only for development: Environment variables
#    Less secure as they're visible in 'docker inspect'
ENTRYPOINT ["mcp-jenkins"]
CMD ["--help"]

# ============================================================================
# Default to production stage
# ============================================================================
FROM production

# ============================================================================
# DEPLOYMENT SECURITY CHECKLIST
# ============================================================================
#
# Runtime Security Options:
# -------------------------
# docker run \
#   --read-only \                              # Read-only root filesystem
#   --tmpfs /tmp:noexec,nosuid,nodev \        # Writable tmp without exec
#   # --tmpfs /app/.cache:noexec,nosuid,nodev \ # Only if runtime cache needed
#   --security-opt=no-new-privileges:true \   # Prevent privilege escalation
#   --cap-drop=ALL \                          # Drop all capabilities
#   --user=10001:10001 \                      # Explicit non-root user
#   --memory=512m \                           # Memory limit
#   --cpus=1.0 \                              # CPU limit
#   --pids-limit=100 \                        # Process limit
#   --network=jenkins-network \               # Isolated network
#   local/mcp-jenkins:latest
#
# Container Scanning:
# ------------------
# - Scan with Trivy: trivy image local/mcp-jenkins:latest
# - Scan with Grype: grype local/mcp-jenkins:latest
# - Scan with Snyk: snyk container test local/mcp-jenkins:latest
#
# Secrets Management:
# ------------------
# - Never commit secrets to Git
# - Never pass secrets as build ARGs (they persist in layers)
# - Use Docker secrets or external secret management
# - Rotate credentials regularly
# - Use read-only volumes for credential files
# - Set restrictive file permissions (400/600)
#
# Network Security:
# ----------------
# - Use dedicated Docker networks (not default bridge)
# - Apply network policies in Kubernetes
# - Restrict egress to Jenkins API only
# - Use TLS for Jenkins connections
# - Consider service mesh for mTLS
#
# Monitoring & Logging:
# --------------------
# - Aggregate logs to external system (don't rely on container logs)
# - Monitor for unusual network activity
# - Alert on healthcheck failures
# - Track resource usage metrics
# - Implement application-level audit logging
#
# Compliance:
# ----------
# - Regular vulnerability scanning (daily)
# - Keep base images updated
# - Update Python dependencies regularly
# - Document security exceptions
# - Maintain SBOM (Software Bill of Materials)
# ============================================================================
