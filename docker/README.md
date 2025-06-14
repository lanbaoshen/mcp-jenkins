# Docker Configuration

This directory contains all Docker-related files for the MCP Jenkins project.

## Files

- **`Dockerfile`** - Multi-stage Docker image definition
- **`docker-bake.hcl`** - Docker Buildx Bake configuration file
- **`docker-compose.yml`** - Docker Compose configuration for easy deployment
- **`.dockerignore`** - Files to exclude from Docker build context
- **`DOCKER.md`** - Comprehensive Docker documentation
- **`../.env`** - Environment file that enables running docker-compose from project root

## Quick Start

From the project root directory:

```bash
# Build using Docker Bake (recommended)
./bake.sh

# Run with Docker Compose (from project root - .env file automatically sets COMPOSE_FILE)
docker-compose up mcp-jenkins
```

For detailed instructions, see [`DOCKER.md`](./DOCKER.md).
