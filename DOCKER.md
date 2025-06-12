# Docker Setup for MCP Jenkins

This directory contains Docker configuration files to containerize the MCP Jenkins application.

## Files

- `Dockerfile` - Multi-stage Docker image definition
- `build.sh` - Comprehensive build script with multiple options
- `bake.sh` - Docker Buildx Bake build script (recommended)
- `docker-bake.hcl` - Buildx Bake configuration file
- `docker-compose.yml` - Docker Compose configuration for easy deployment
- `.dockerignore` - Files to exclude from Docker build context

## Quick Start

### 1. Build the Docker Image

#### Using Docker Buildx Bake (Recommended)

```bash
# Basic build
./bake.sh

# Build development image
./bake.sh mcp-jenkins-dev

# Build with custom tag
./bake.sh --tag v1.0.0

# Build for multiple architectures
./bake.sh mcp-jenkins-multi

# Build and push to registry
./bake.sh --tag v1.0.0 --push --registry your-registry.com

# Build with GitHub Actions cache
./bake.sh --cache-from gha --cache-to gha

# Print configuration without building
./bake.sh --print

# Build all targets
./bake.sh all
```

#### Using Traditional Build Script

```bash
# Basic build
./build.sh

# Build with custom tag
./build.sh --tag v1.0.0

# Build for multiple architectures
./build.sh --platform linux/amd64,linux/arm64

# Build without cache
./build.sh --no-cache

# Build and push to registry
./build.sh --tag v1.0.0 --push --registry your-registry.com
```

### 2. Run the Container

#### Using Docker directly:

```bash
# Stdio mode (default)
docker run --rm local/mcp-jenkins:latest \
  --jenkins-url https://your-jenkins.example.com \
  --jenkins-username your-username \
  --jenkins-password your-password

# SSE mode with port mapping
docker run --rm -p 9887:9887 local/mcp-jenkins:latest \
  --jenkins-url https://your-jenkins.example.com \
  --jenkins-username your-username \
  --jenkins-password your-password \
  --transport sse \
  --port 9887
```
  --port 9887
```

#### Using Docker Compose:

```bash
# Set environment variables
export JENKINS_URL="https://your-jenkins.example.com"
export JENKINS_USERNAME="your-username"
export JENKINS_PASSWORD="your-password"

# Run in stdio mode
docker-compose up mcp-jenkins

# Run in SSE mode (modify docker-compose.yml first)
docker-compose up mcp-jenkins

# Run development version
docker-compose --profile development up mcp-jenkins-dev
```

### 3. Environment Variables

You can use environment variables instead of command-line arguments:

```bash
docker run --rm \
  -e JENKINS_URL="https://your-jenkins.example.com" \
  -e JENKINS_USERNAME="your-username" \
  -e JENKINS_PASSWORD="your-password" \
  local/mcp-jenkins:latest
```

## Build Script Options

The `build.sh` script supports various options:

```bash
./build.sh --help
```

### Common Use Cases

```bash
# Development build with all dependencies
./build.sh --tag dev --build-arg TARGET=development

# Production build (default)
./build.sh --tag latest

# Multi-architecture build for registry
./build.sh --tag v1.0.0 --platform linux/amd64,linux/arm64 --push --registry your-registry.com

# Clean build without cache
./build.sh --no-cache --clean
```

## Multi-Stage Build

The Dockerfile includes two stages:

- **development**: Includes dev dependencies and tools for development
- **production**: Minimal dependencies for production use (default)

To build development image:
```bash
docker build --target development -t mcp-jenkins:dev .
```

## Docker Buildx Bake

Docker Buildx Bake provides a more powerful and flexible way to build Docker images with advanced features like multi-platform builds, caching strategies, and complex build configurations.

### Bake Configuration

The `docker-bake.hcl` file defines several build targets:

- **mcp-jenkins**: Production image (default)
- **mcp-jenkins-dev**: Development image with dev dependencies
- **mcp-jenkins-multi**: Multi-architecture build (linux/amd64, linux/arm64)
- **all**: Builds both production and development images

### Bake Script Features

The `bake.sh` script provides:

- **Multi-platform builds**: Easy cross-platform compilation
- **Advanced caching**: GitHub Actions, registry, and local cache support
- **Variable configuration**: Flexible build-time variables
- **Target selection**: Build specific targets or all at once
- **Configuration preview**: See what will be built without building

### Bake Usage Examples

```bash
# Show help
./bake.sh --help

# Build production image
./bake.sh

# Build development image
./bake.sh mcp-jenkins-dev

# Multi-architecture build
./bake.sh mcp-jenkins-multi

# Build with registry push
./bake.sh --tag v1.0.0 --registry ghcr.io/your-org --push

# Build with caching
./bake.sh --cache-from gha --cache-to gha

# Preview build configuration
./bake.sh --print

# Build all targets
./bake.sh all
```

### Cache Strategies

#### GitHub Actions Cache
```bash
./bake.sh --cache-from gha --cache-to gha
```

#### Registry Cache
```bash
./bake.sh --cache-from registry --cache-to registry --registry your-registry.com
```

#### Local Cache
```bash
./bake.sh --cache-from local --cache-to local
```

## Security Considerations

- The container runs as a non-root user (`appuser`)
- Sensitive credentials should be passed as environment variables or mounted secrets
- Consider using Docker secrets or external secret management for production

## Troubleshooting

### Build Issues

1. **Docker daemon not running**:
   ```bash
   sudo systemctl start docker
   ```

2. **Permission denied**:
   ```bash
   sudo usermod -aG docker $USER
   # Log out and back in
   ```

3. **Build cache issues**:
   ```bash
   ./build.sh --no-cache
   ```

### Runtime Issues

1. **Check logs**:
   ```bash
   docker logs <container-id>
   ```

2. **Debug inside container**:
   ```bash
   docker run -it --entrypoint /bin/bash local/mcp-jenkins:latest
   ```

3. **Health check**:
   ```bash
   docker inspect --format='{{.State.Health.Status}}' <container-id>
   ```

## Development Workflow

1. **Build development image**:
   ```bash
   ./build.sh --tag dev --build-arg TARGET=development
   ```

2. **Run with code mounting**:
   ```bash
   docker run -it --rm \
     -v $(pwd)/src:/app/src \
     -p 9887:9887 \
     local/mcp-jenkins:dev \
     --jenkins-url https://your-jenkins.example.com \
     --jenkins-username your-username \
     --jenkins-password your-password \
     --transport sse
   ```

3. **Use Docker Compose for development**:
   ```bash
   docker-compose --profile development up mcp-jenkins-dev
   ```
