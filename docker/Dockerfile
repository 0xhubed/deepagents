# DeepAgents CLI Docker Image
# Provides a Linux environment for running DeepAgents on Windows

FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create workspace directory
WORKDIR /workspace

# Install Python dependencies
# Install deepagents-cli from local source (with Ollama support)
COPY libs/deepagents /tmp/deepagents
COPY libs/cli /tmp/deepagents-cli

RUN pip install /tmp/deepagents && \
    pip install "/tmp/deepagents-cli[ollama]" && \
    rm -rf /tmp/deepagents /tmp/deepagents-cli

# Install additional utilities
RUN pip install \
    pandas \
    openpyxl \
    xlrd

# Create non-root user for security
RUN useradd -m -s /bin/bash agent && \
    chown -R agent:agent /workspace

USER agent

# Set default working directory
WORKDIR /workspace

# Default command - run deepagents CLI
ENTRYPOINT ["deepagents"]
