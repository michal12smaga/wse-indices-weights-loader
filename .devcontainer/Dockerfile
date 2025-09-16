# Note: This Dockerfile is not used by default.
# To use it, comment out the "image" line and uncomment the "build" section 
# in devcontainer.json

FROM mcr.microsoft.com/devcontainers/python:3.11

# Install additional OS packages
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    make \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install uv