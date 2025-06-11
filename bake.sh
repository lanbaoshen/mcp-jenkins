#!/bin/bash

# MCP Jenkins Docker Bake Build Script
# This script uses Docker Buildx Bake for building images

set -euo pipefail

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
MCP Jenkins Docker Bake Build Script

Usage: $0 [OPTIONS] [TARGET]

TARGETS:
    mcp-jenkins         Build production image (default)
    mcp-jenkins-dev     Build development image
    mcp-jenkins-multi   Build multi-architecture image
    all                 Build both production and development images

OPTIONS:
    -t, --tag TAG           Docker image tag (default: latest)
    -r, --registry URL      Registry URL for pushing
    -p, --push              Push image to registry after building
    --platform PLATFORMS   Target platforms (comma-separated, e.g., linux/amd64,linux/arm64)
    --cache-from TYPE       Cache source type (gha, registry, local)
    --cache-to TYPE         Cache destination type (gha, registry, local)
    --print                 Print the build configuration without building
    --progress MODE         Progress output mode (auto, plain, tty)
    -h, --help              Show this help message

EXAMPLES:
    # Basic build
    $0

    # Build development image
    $0 mcp-jenkins-dev

    # Build with custom tag
    $0 --tag v1.0.0

    # Build and push to registry
    $0 --tag v1.0.0 --push --registry your-registry.com

    # Multi-architecture build
    $0 mcp-jenkins-multi

    # Build with GitHub Actions cache
    $0 --cache-from gha --cache-to gha

    # Print configuration without building
    $0 --print

    # Build all targets
    $0 all

EOF
}

# Default values
TARGET="mcp-jenkins"
TAG="latest"
REGISTRY=""
PUSH="false"
PLATFORM=""
CACHE_FROM=""
CACHE_TO=""
PRINT_ONLY="false"
PROGRESS="auto"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -p|--push)
            PUSH="true"
            shift
            ;;
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        --cache-from)
            CACHE_FROM="$2"
            shift 2
            ;;
        --cache-to)
            CACHE_TO="$2"
            shift 2
            ;;
        --print)
            PRINT_ONLY="true"
            shift
            ;;
        --progress)
            PROGRESS="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        mcp-jenkins|mcp-jenkins-dev|mcp-jenkins-multi|all)
            TARGET="$1"
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if Docker Buildx is available
if ! docker buildx version &> /dev/null; then
    log_error "Docker Buildx is not available. Please install Docker Buildx."
    exit 1
fi

# Check if bake file exists
BAKE_FILE="docker-bake.hcl"
if [[ ! -f "${BAKE_FILE}" ]]; then
    log_error "Bake file not found: ${BAKE_FILE}"
    exit 1
fi

# Prepare build variables
BUILD_VARS=()
BUILD_VARS+=("TAG=${TAG}")

if [[ -n "${REGISTRY}" ]]; then
    BUILD_VARS+=("REGISTRY=${REGISTRY}")
fi

if [[ "${PUSH}" == "true" ]]; then
    BUILD_VARS+=("PUSH=${PUSH}")
fi

if [[ -n "${PLATFORM}" ]]; then
    # Convert comma-separated platforms to array format for HCL
    PLATFORM_ARRAY="[\"$(echo "${PLATFORM}" | sed 's/,/","/g')\"]"
    BUILD_VARS+=("PLATFORM=${PLATFORM_ARRAY}")
fi

if [[ -n "${CACHE_FROM}" ]]; then
    case "${CACHE_FROM}" in
        gha)
            BUILD_VARS+=("CACHE_FROM=[\"type=gha\"]")
            ;;
        registry)
            if [[ -n "${REGISTRY}" ]]; then
                BUILD_VARS+=("CACHE_FROM=[\"type=registry,ref=${REGISTRY}/mcp-jenkins:cache\"]")
            else
                log_warning "Registry cache requires --registry to be set"
            fi
            ;;
        local)
            BUILD_VARS+=("CACHE_FROM=[\"type=local,src=/tmp/.buildx-cache\"]")
            ;;
        *)
            BUILD_VARS+=("CACHE_FROM=[\"${CACHE_FROM}\"]")
            ;;
    esac
fi

if [[ -n "${CACHE_TO}" ]]; then
    case "${CACHE_TO}" in
        gha)
            BUILD_VARS+=("CACHE_TO=[\"type=gha,mode=max\"]")
            ;;
        registry)
            if [[ -n "${REGISTRY}" ]]; then
                BUILD_VARS+=("CACHE_TO=[\"type=registry,ref=${REGISTRY}/mcp-jenkins:cache,mode=max\"]")
            else
                log_warning "Registry cache requires --registry to be set"
            fi
            ;;
        local)
            BUILD_VARS+=("CACHE_TO=[\"type=local,dest=/tmp/.buildx-cache,mode=max\"]")
            ;;
        *)
            BUILD_VARS+=("CACHE_TO=[\"${CACHE_TO}\"]")
            ;;
    esac
fi

# Build the command
BAKE_CMD="docker buildx bake"
BAKE_CMD+=" --file ${BAKE_FILE}"
BAKE_CMD+=" --progress ${PROGRESS}"

# Add variables
for var in "${BUILD_VARS[@]}"; do
    BAKE_CMD+=" --set *.args.${var}"
done

BAKE_CMD+=" ${TARGET}"

# Print configuration if requested
if [[ "${PRINT_ONLY}" == "true" ]]; then
    log_info "Build configuration:"
    echo "Target: ${TARGET}"
    echo "Tag: ${TAG}"
    echo "Registry: ${REGISTRY:-<none>}"
    echo "Push: ${PUSH}"
    echo "Platform: ${PLATFORM:-<default>}"
    echo "Cache From: ${CACHE_FROM:-<none>}"
    echo "Cache To: ${CACHE_TO:-<none>}"
    echo ""
    log_info "Bake command:"
    echo "${BAKE_CMD}"
    echo ""
    log_info "Bake configuration preview:"
    docker buildx bake --file "${BAKE_FILE}" --print "${TARGET}" 2>/dev/null || log_warning "Could not print bake configuration"
    exit 0
fi

# Show build information
log_info "Starting Docker Buildx Bake..."
log_info "Target: ${TARGET}"
log_info "Tag: ${TAG}"
log_info "Registry: ${REGISTRY:-<none>}"
log_info "Push: ${PUSH}"
if [[ -n "${PLATFORM}" ]]; then
    log_info "Platform: ${PLATFORM}"
fi

# Execute build
log_info "Building with Docker Buildx Bake..."
log_info "Command: ${BAKE_CMD}"

if eval "${BAKE_CMD}"; then
    log_success "Docker build completed successfully!"

    # Show built images
    log_info "Built images:"
    if [[ "${TARGET}" == "all" ]]; then
        docker images "local/mcp-jenkins" --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}"
    else
        IMAGE_NAME="local/mcp-jenkins"
        if [[ "${TARGET}" == "mcp-jenkins-dev" ]]; then
            IMAGE_NAME="local/mcp-jenkins"
        fi
        docker images "${IMAGE_NAME}" --filter "reference=*:${TAG}*" --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}"
    fi

    # Show usage examples
    if [[ "${PUSH}" != "true" ]]; then
        log_info "Usage examples:"
        if [[ -n "${REGISTRY}" ]]; then
            IMAGE_REF="${REGISTRY}/mcp-jenkins:${TAG}"
        else
            IMAGE_REF="local/mcp-jenkins:${TAG}"
        fi

        echo "  # Run in stdio mode:"
        echo "  docker run --rm ${IMAGE_REF} --jenkins-url https://jenkins.example.com --jenkins-username user --jenkins-password pass"
        echo ""
        echo "  # Run in SSE mode:"
        echo "  docker run --rm -p 9887:9887 ${IMAGE_REF} --jenkins-url https://jenkins.example.com --jenkins-username user --jenkins-password pass --transport sse"
    fi

else
    log_error "Docker build failed"
    exit 1
fi

log_success "Build process completed!"
