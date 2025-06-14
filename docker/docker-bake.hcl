variable "TAG" {
  default = "latest"
}

variable "REGISTRY" {
  default = ""
}

variable "PLATFORM" {
  default = ["linux/amd64"]
}

variable "PUSH" {
  default = false
}

variable "CACHE_FROM" {
  default = []
}

variable "CACHE_TO" {
  default = []
}

group "default" {
  targets = ["mcp-jenkins"]
}

group "all" {
  targets = ["mcp-jenkins", "mcp-jenkins-dev"]
}

target "docker-metadata-action" {
  tags = ["local/mcp-jenkins:${TAG}"]
}

target "mcp-jenkins" {
  inherits = ["docker-metadata-action"]
  context = ".."
  dockerfile = "docker/Dockerfile"
  target = "production"
  platforms = PLATFORM
  tags = REGISTRY != "" ? ["${REGISTRY}/mcp-jenkins:${TAG}"] : ["local/mcp-jenkins:${TAG}"]
  cache-from = CACHE_FROM
  cache-to = CACHE_TO
  output = PUSH ? ["type=registry"] : ["type=docker"]
  labels = {
    "org.opencontainers.image.title" = "MCP Jenkins"
    "org.opencontainers.image.description" = "Model Context Protocol (MCP) implementation for Jenkins"
    "org.opencontainers.image.vendor" = "lanbaoshen"
    "org.opencontainers.image.licenses" = "MIT"
    "org.opencontainers.image.source" = "https://github.com/lanbaoshen/mcp-jenkins"
  }
}

target "mcp-jenkins-dev" {
  inherits = ["mcp-jenkins"]
  target = "development"
  tags = REGISTRY != "" ? ["${REGISTRY}/mcp-jenkins:${TAG}-dev"] : ["local/mcp-jenkins:${TAG}-dev"]
  output = ["type=docker"]
}

target "mcp-jenkins-multi" {
  inherits = ["mcp-jenkins"]
  platforms = ["linux/amd64", "linux/arm64"]
}

target "mcp-jenkins-cache" {
  inherits = ["mcp-jenkins"]
  cache-from = ["type=gha"]
  cache-to = ["type=gha,mode=max"]
}

target "mcp-jenkins-registry" {
  inherits = ["mcp-jenkins"]
  cache-from = ["type=registry,ref=${REGISTRY}/mcp-jenkins:cache"]
  cache-to = ["type=registry,ref=${REGISTRY}/mcp-jenkins:cache,mode=max"]
}
