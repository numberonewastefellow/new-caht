# Two stages: compilers/headers/curl are only needed to BUILD the scientific stack.
# The runtime image that executes untrusted user code ships none of them (every
# package installs from a manylinux wheel with its native libs vendored in
# <pkg>.libs/, so nothing links against the build-stage system libraries).

# ---- build stage -------------------------------------------------------------
FROM python:3.11-slim AS build

# Install build prerequisites and uv for dependency management
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        gfortran \
        libfreetype6-dev \
        liblapack-dev \
        libopenblas-dev \
        libpng-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /tmp/*

ENV PATH="/root/.local/bin:${PATH}"

# Pre-install the scientific stack via uv using a dedicated lockfile
COPY pyproject.toml uv.lock /tmp/executor/
RUN uv sync --directory /tmp/executor \
        --no-dev \
        --frozen \
    && mv /tmp/executor/.venv /opt/executor-venv \
    && rm -rf /tmp/executor

# ---- runtime stage -----------------------------------------------------------
# Same base image as the build stage, so the venv's interpreter symlinks resolve.
FROM python:3.11-slim

# procps: `pkill`, used by the service to stop a timed-out run inside the sandbox.
RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /opt/executor-venv /opt/executor-venv

ENV VIRTUAL_ENV="/opt/executor-venv"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
