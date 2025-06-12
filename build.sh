#!/bin/bash

# MCP Jenkins Docker Build Script
# This script builds and optionally pushes the MCP Jenkins Docker image

set -euo pipefail

# Configuration
IMAGE_NAME="mcp-jenkins"
DEFAULT_TAG="latest"
DOCKERFILE="Dockerfile"
BUILD_CONTEXT="."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    cat << EOF
MCP Jenkins Docker Build Script

Usage: $0 [OPTIONS]

OPTIONS:
    -t, --tag TAG           Docker image tag (default: ${DEFAULT_TAG})
    -n, --name NAME         Docker image name (default: ${IMAGE_NAME})
    -f, --file FILE         Dockerfile path (default: ${DOCKERFILE})
    -c, --context PATH      Build context path (default: ${BUILD_CONTEXT})
    -p, --push              Push image to registry after building
    -r, --registry URL      Registry URL for pushing (e.g., your-registry.com)
    --no-cache             Build without using cache
    --platform PLATFORMS   Target platforms for multi-arch build (e.g., linux/amd64,linux/arm64)
    --build-arg ARG=VALUE   Pass build argument
    --clean                 Clean up dangling images after build
    -h, --help              Show this help message

EXAMPLES:
    # Basic build
    $0

    # Build with custom tag
    $0 --tag v1.0.0

    # Build and push to registry
    $0 --tag v1.0.0 --push --registry your-registry.com

    # Multi-architecture build
    $0 --platform linux/amd64,linux/arm64

    # Build without cache
    $0 --no-cache

    # Build with custom build args
    $0 --build-arg PYTHON_VERSION=3.11

EOF
}

# Parse command line arguments
TAG="${DEFAULT_TAG}"
REGISTRY=""
PUSH=false
NO_CACHE=""
PLATFORM=""
BUILD_ARGS=()
CLEAN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -f|--file)
            DOCKERFILE="$2"
            shift 2
            ;;
        -c|--context)
            BUILD_CONTEXT="$2"
            shift 2
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --platform)
            PLATFORM="--platform $2"
            shift 2
            ;;
        --build-arg)
            BUILD_ARGS+=("--build-arg" "$2")
            shift 2
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate inputs
if [[ ! -f "${DOCKERFILE}" ]]; then
    log_error "Dockerfile not found: ${DOCKERFILE}"
    exit 1
fi

if [[ ! -d "${BUILD_CONTEXT}" ]]; then
    log_error "Build context directory not found: ${BUILD_CONTEXT}"
    exit 1
fi

# Set full image name
if [[ -n "${REGISTRY}" ]]; then
    FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}:${TAG}"
else
    FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    log_error "Docker daemon is not running"
    exit 1
fi

# Build command construction
BUILD_CMD="docker build"
BUILD_CMD+=" -f ${DOCKERFILE}"
BUILD_CMD+=" -t ${FULL_IMAGE_NAME}"
BUILD_CMD+=" ${NO_CACHE}"
BUILD_CMD+=" ${PLATFORM}"

# Add build args
for arg in "${BUILD_ARGS[@]}"; do
    BUILD_CMD+=" ${arg}"
done

BUILD_CMD+=" ${BUILD_CONTEXT}"

# Show build information
log_info "Starting Docker build..."
log_info "Image name: ${FULL_IMAGE_NAME}"
log_info "Dockerfile: ${DOCKERFILE}"
log_info "Build context: ${BUILD_CONTEXT}"
log_info "Build command: ${BUILD_CMD}"

# Execute build
log_info "Building Docker image..."
if eval "${BUILD_CMD}"; then
    log_success "Docker image built successfully: ${FULL_IMAGE_NAME}"
else
    log_error "Docker build failed"
    exit 1
fi

# Push if requested
if [[ "${PUSH}" == true ]]; then
    if [[ -z "${REGISTRY}" ]]; then
        log_warning "No registry specified, pushing to Docker Hub"
    fi

    log_info "Pushing image to registry..."
    if docker push "${FULL_IMAGE_NAME}"; then
        log_success "Image pushed successfully: ${FULL_IMAGE_NAME}"
    else
        log_error "Failed to push image"
        exit 1
    fi
fi

# Clean up if requested
if [[ "${CLEAN}" == true ]]; then
    log_info "Cleaning up dangling images..."
    if docker image prune -f; then
        log_success "Cleanup completed"
    else
        log_warning "Cleanup had some issues"
    fi
fi

# Show image information
log_info "Image information:"
docker images "${IMAGE_NAME}" --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}"

# Show usage examples
log_info "Usage examples:"
echo "  # Run in stdio mode:"
echo "  docker run --rm ${FULL_IMAGE_NAME} --jenkins-url https://jenkins.example.com --jenkins-username user --jenkins-password pass"
echo ""
echo "  # Run in SSE mode:"
echo "  docker run --rm -p 9887:9887 ${FULL_IMAGE_NAME} --jenkins-url https://jenkins.example.com --jenkins-username user --jenkins-password pass --transport sse"
echo ""
echo "  # Run with environment variables:"
echo "  docker run --rm -e JENKINS_URL=https://jenkins.example.com -e JENKINS_USERNAME=user -e JENKINS_PASSWORD=pass ${FULL_IMAGE_NAME}"

log_success "Build process completed!"
