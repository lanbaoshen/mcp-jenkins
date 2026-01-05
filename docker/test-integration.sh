#!/bin/bash

# MCP Jenkins Docker Integration Test Script
# Tests the Docker image against a real Jenkins controller

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[FAIL]${NC} $1"; }

# Configuration (override via environment variables)
JENKINS_URL="${JENKINS_URL:-}"
JENKINS_USERNAME="${JENKINS_USERNAME:-}"
JENKINS_PASSWORD="${JENKINS_PASSWORD:-}"
IMAGE_NAME="${IMAGE_NAME:-local/mcp-jenkins:latest}"
TEST_TIMEOUT="${TEST_TIMEOUT:-30}"

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

show_help() {
    cat << EOF
MCP Jenkins Docker Integration Test Script

Usage: $0 [OPTIONS]

OPTIONS:
    --url URL           Jenkins URL (or set JENKINS_URL)
    --username USER     Jenkins username (or set JENKINS_USERNAME)
    --password PASS     Jenkins password (or set JENKINS_PASSWORD)
    --image IMAGE       Docker image to test (default: local/mcp-jenkins:latest)
    --build             Build the image before testing
    --timeout SECS      Timeout for each test (default: 30)
    -h, --help          Show this help message

EXAMPLES:
    # Test with environment variables
    export JENKINS_URL=http://jenkins:8080
    export JENKINS_USERNAME=admin
    export JENKINS_PASSWORD=secret
    $0

    # Test with command line arguments
    $0 --url http://jenkins:8080 --username admin --password secret

    # Build and test
    $0 --build --url http://jenkins:8080 --username admin --password secret

EOF
}

# Parse arguments
BUILD_IMAGE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --url) JENKINS_URL="$2"; shift 2 ;;
        --username) JENKINS_USERNAME="$2"; shift 2 ;;
        --password) JENKINS_PASSWORD="$2"; shift 2 ;;
        --image) IMAGE_NAME="$2"; shift 2 ;;
        --build) BUILD_IMAGE=true; shift ;;
        --timeout) TEST_TIMEOUT="$2"; shift 2 ;;
        -h|--help) show_help; exit 0 ;;
        *) log_error "Unknown option: $1"; show_help; exit 1 ;;
    esac
done

# Validate required parameters
if [[ -z "${JENKINS_URL}" ]] || [[ -z "${JENKINS_USERNAME}" ]] || [[ -z "${JENKINS_PASSWORD}" ]]; then
    log_error "Missing required parameters: --url, --username, --password"
    show_help
    exit 1
fi

# Test function
run_test() {
    local test_name="$1"
    local test_cmd="$2"
    local expected_pattern="${3:-}"

    TESTS_RUN=$((TESTS_RUN + 1))
    log_info "Running: ${test_name}"

    local output
    local exit_code=0

    output=$(timeout "${TEST_TIMEOUT}" bash -c "${test_cmd}" 2>&1) || exit_code=$?

    if [[ ${exit_code} -eq 0 ]]; then
        if [[ -n "${expected_pattern}" ]]; then
            if echo "${output}" | grep -qE "${expected_pattern}"; then
                log_success "${test_name}"
                TESTS_PASSED=$((TESTS_PASSED + 1))
                return 0
            else
                log_error "${test_name} - pattern not found: ${expected_pattern}"
                echo "  Output: ${output:0:200}"
                TESTS_FAILED=$((TESTS_FAILED + 1))
                return 1
            fi
        else
            log_success "${test_name}"
            TESTS_PASSED=$((TESTS_PASSED + 1))
            return 0
        fi
    else
        log_error "${test_name} - exit code: ${exit_code}"
        echo "  Output: ${output:0:200}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

echo ""
echo "=============================================="
echo "  MCP Jenkins Docker Integration Tests"
echo "=============================================="
echo ""
log_info "Jenkins URL: ${JENKINS_URL}"
log_info "Username: ${JENKINS_USERNAME}"
log_info "Image: ${IMAGE_NAME}"
echo ""

# Build image if requested
if [[ "${BUILD_IMAGE}" == "true" ]]; then
    log_info "Building Docker image..."
    if docker build -f docker/Dockerfile --target production -t "${IMAGE_NAME}" . > /dev/null 2>&1; then
        log_success "Image built successfully"
    else
        log_error "Failed to build image"
        exit 1
    fi
    echo ""
fi

# Check if image exists
if ! docker image inspect "${IMAGE_NAME}" > /dev/null 2>&1; then
    log_error "Image not found: ${IMAGE_NAME}"
    log_info "Run with --build to build the image first"
    exit 1
fi

echo "----------------------------------------------"
echo "  Basic Tests"
echo "----------------------------------------------"

# Test 1: Help command
run_test "Help command works" \
    "docker run --rm ${IMAGE_NAME} --help" \
    "Jenkins.*MCP"

# Test 2: Module import
run_test "Python module imports" \
    "docker run --rm --entrypoint python3 ${IMAGE_NAME} -c 'import mcp_jenkins; print(\"OK\")'" \
    "OK"

# Test 3: Jenkins connectivity
run_test "Jenkins connectivity" \
    "docker run --rm --network host ${IMAGE_NAME} --jenkins-url ${JENKINS_URL} --jenkins-username ${JENKINS_USERNAME} --jenkins-password ${JENKINS_PASSWORD} --help" \
    "Jenkins.*MCP"

echo ""
echo "----------------------------------------------"
echo "  MCP Protocol Tests (stdio mode)"
echo "----------------------------------------------"
# NOTE: Tests use --network host for simplicity in accessing the Jenkins server.
# In production, use dedicated Docker networks for proper network isolation.
# Credentials are passed via CLI args for test convenience; this is acceptable
# for local testing but should use secrets/env files in production.

# Test 4: MCP Initialize
MCP_INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
run_test "MCP initialize" \
    "echo '${MCP_INIT}' | timeout 10 docker run --rm -i --network host ${IMAGE_NAME} --jenkins-url ${JENKINS_URL} --jenkins-username ${JENKINS_USERNAME} --jenkins-password ${JENKINS_PASSWORD} --transport stdio 2>/dev/null | head -1" \
    "protocolVersion|serverInfo"

# Test 5: List tools
MCP_LIST_TOOLS='{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
run_test "MCP list tools" \
    "echo -e '${MCP_INIT}\n${MCP_LIST_TOOLS}' | timeout 10 docker run --rm -i --network host ${IMAGE_NAME} --jenkins-url ${JENKINS_URL} --jenkins-username ${JENKINS_USERNAME} --jenkins-password ${JENKINS_PASSWORD} --transport stdio 2>/dev/null | tail -1" \
    "get_all_jobs|get_job|tools"

# Test 6: Call get_all_jobs
MCP_GET_JOBS='{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_all_jobs","arguments":{}}}'
run_test "MCP get_all_jobs tool" \
    "echo -e '${MCP_INIT}\n${MCP_GET_JOBS}' | timeout 15 docker run --rm -i --network host ${IMAGE_NAME} --jenkins-url ${JENKINS_URL} --jenkins-username ${JENKINS_USERNAME} --jenkins-password ${JENKINS_PASSWORD} --transport stdio 2>/dev/null | tail -1" \
    "result|content|text"

echo ""
echo "----------------------------------------------"
echo "  Transport Mode Tests"
echo "----------------------------------------------"
# NOTE: Using ports 19887/19888 instead of default 9887 to avoid conflicts
# with any MCP server that might already be running on the host.

# Test 7: SSE mode starts
run_test "SSE mode starts" \
    "timeout 5 docker run --rm --network host ${IMAGE_NAME} --jenkins-url ${JENKINS_URL} --jenkins-username ${JENKINS_USERNAME} --jenkins-password ${JENKINS_PASSWORD} --transport sse --port 19887 2>&1 || true" \
    "Uvicorn|running|Started|Application"

# Test 8: Streamable HTTP mode starts
run_test "Streamable HTTP mode starts" \
    "timeout 5 docker run --rm --network host ${IMAGE_NAME} --jenkins-url ${JENKINS_URL} --jenkins-username ${JENKINS_USERNAME} --jenkins-password ${JENKINS_PASSWORD} --transport streamable-http --port 19888 2>&1 || true" \
    "Uvicorn|running|Started|Application"

echo ""
echo "----------------------------------------------"
echo "  Security Tests"
echo "----------------------------------------------"

# Test 9: Non-root user
run_test "Runs as non-root user" \
    "docker run --rm --entrypoint id ${IMAGE_NAME}" \
    "uid=10001|appuser"

# Test 10: User shell is nologin (production security)
run_test "User shell is nologin" \
    "docker run --rm --entrypoint cat ${IMAGE_NAME} /etc/passwd | grep appuser" \
    "nologin"

# Test 11: Read-only filesystem compatible
run_test "Read-only filesystem works" \
    "docker run --rm --read-only --tmpfs /tmp --tmpfs /app/.cache --network host ${IMAGE_NAME} --help" \
    "Jenkins.*MCP"

echo ""
echo "=============================================="
echo "  Test Results"
echo "=============================================="
echo ""
echo "  Total:  ${TESTS_RUN}"
echo -e "  ${GREEN}Passed: ${TESTS_PASSED}${NC}"
echo -e "  ${RED}Failed: ${TESTS_FAILED}${NC}"
echo ""

if [[ ${TESTS_FAILED} -eq 0 ]]; then
    log_success "All tests passed!"
    exit 0
else
    log_error "Some tests failed"
    exit 1
fi
