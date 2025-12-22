FROM debian:trixie

LABEL maintainer="SigmaVault Project"
LABEL description="Build environment for SigmaVault NAS OS"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    build-essential \
    devscripts \
    debhelper \
    dh-python \
    python3-all \
    python3-setuptools \
    python3-pip \
    python3-venv \
    golang-go \
    nodejs \
    npm \
    live-build \
    cdebootstrap \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install pnpm for frontend builds
RUN npm install -g pnpm

WORKDIR /build

COPY . .

CMD ["./scripts/build-all.sh"]
