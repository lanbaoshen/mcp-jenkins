# Multi-stage Dockerfile for MCP Jenkins

# Base stage with common dependencies
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Development stage
FROM base as development

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install all dependencies (including dev)
RUN uv sync --frozen

# Copy source code
COPY src/ ./src/
COPY README.md LICENSE ./

# Install the package in development mode
RUN uv pip install -e .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose default SSE port
EXPOSE 9887

# Default command for development
ENTRYPOINT ["uv", "run", "mcp-jenkins"]
CMD ["--help"]

# Production stage
FROM base as production

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install only production dependencies
RUN uv sync --frozen --no-dev

# Copy source code
COPY src/ ./src/
COPY README.md LICENSE ./

# Install the package
RUN uv pip install -e .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose default SSE port
EXPOSE 9887

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import mcp_jenkins; print('OK')" || exit 1

# Default command (can be overridden)
ENTRYPOINT ["uv", "run", "mcp-jenkins"]
CMD ["--help"]

# Default to production stage
FROM production
