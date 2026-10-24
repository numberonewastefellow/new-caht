group "default" {
  targets = ["backend", "web"]
}

variable "BACKEND_REPOSITORY" {
  default = "om/om-backend"
}

variable "WEB_SERVER_REPOSITORY" {
  default = "om/om-web-server"
}

variable "INTEGRATION_REPOSITORY" {
  default = "om/om-integration"
}

variable "TAG" {
  default = "latest"
}

target "backend" {
  context    = "backend"
  dockerfile = "Dockerfile"

  cache-from = ["type=registry,ref=${BACKEND_REPOSITORY}:latest"]
  cache-to   = ["type=inline"]

  tags      = ["${BACKEND_REPOSITORY}:${TAG}"]
}

target "web" {
  context    = "web"
  dockerfile = "Dockerfile"

  cache-from = ["type=registry,ref=${WEB_SERVER_REPOSITORY}:latest"]
  cache-to   = ["type=inline"]

  tags      = ["${WEB_SERVER_REPOSITORY}:${TAG}"]
}

target "integration" {
  context    = "backend"
  dockerfile = "tests/integration/Dockerfile"

  // Provide the base image via build context from the backend target
  contexts = {
    base = "target:backend"
  }

  tags      = ["${INTEGRATION_REPOSITORY}:${TAG}"]
}
