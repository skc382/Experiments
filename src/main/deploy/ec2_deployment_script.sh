#!/bin/bash

# Script to install Docker on Ubuntu 20.04, 22.04, or 24.04 LTS

# Exit on any error
set -e

# Check if running as root or with sudo
if [ "$(id -u)" != "0" ]; then
    echo "This script must be run as root or with sudo." >&2
    exit 1
fi

# Update package index
echo "Updating package index..."
apt-get update

# Install required packages
echo "Installing prerequisite packages..."
apt-get install -y ca-certificates curl

# Create directory for Docker GPG key
echo "Adding Docker GPG key..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# Add Docker repository to APT sources
echo "Setting up Docker repository..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index again
echo "Updating package index with Docker repository..."
apt-get update

# Install Docker packages
echo "Installing Docker..."
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verify Docker installation
echo "Verifying Docker installation..."
docker --version

# Test Docker with hello-world container
echo "Running Docker hello-world test..."
docker run hello-world

# Add current user to docker group (optional, for non-root access)
echo "Adding current user to docker group..."
usermod -aG docker ${SUDO_USER:-$USER}

echo "Docker installation completed successfully!"

sudo apt install git-all
echo "Git installation completed successfully!"

echo "Git clone from: https://github.com/skc382/Experiments.git"
git clone https://github.com/skc382/Experiments.git

echo "cd into folder: Experiments/src/experiment/bedrock"
cd Experiments/

echo "Run docker compose upt"
docker compose up -d

echo "Sleeping for 10 seconds"
sleep 15

echo "Check if the app is deployed"
curl http://localhost:5000/api/websocket
