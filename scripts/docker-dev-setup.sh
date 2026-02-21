#!/bin/bash
# Docker Development Setup for United Way Frappe App
# Run this from the UW_Frappe project root

set -e

echo "============================================"
echo "United Way Frappe - Docker Dev Setup"
echo "============================================"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Install Docker Desktop first:"
    echo "  https://docs.docker.com/desktop/"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "Docker Compose not found. Install Docker Compose V2."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Project directory: $PROJECT_DIR"

# Clone frappe_docker if not present
if [ ! -d "$PROJECT_DIR/frappe_docker" ]; then
    echo "Cloning frappe_docker..."
    git clone https://github.com/frappe/frappe_docker.git "$PROJECT_DIR/frappe_docker"
fi

cd "$PROJECT_DIR/frappe_docker"

# Create development compose override that mounts our custom app
cat > compose.custom.yaml << 'EOF'
services:
  backend:
    volumes:
      - ../united_way:/workspace/development/frappe-bench/apps/united_way
  frontend:
    volumes:
      - ../united_way:/workspace/development/frappe-bench/apps/united_way
EOF

# Create .env if not exists
if [ ! -f .env ]; then
    cp example.env .env
fi

echo ""
echo "Starting Docker containers..."
docker compose -f compose.yaml \
  -f overrides/compose.noproxy.yaml \
  -f overrides/compose.mariadb.yaml \
  -f overrides/compose.redis.yaml \
  -f compose.custom.yaml \
  up -d

echo ""
echo "Waiting for services to be ready..."
sleep 15

echo ""
echo "Creating site..."
docker compose exec backend bench new-site uw.localhost \
  --mariadb-root-password 123 \
  --admin-password admin \
  --no-mariadb-socket || true

echo ""
echo "Installing app..."
docker compose exec backend bench --site uw.localhost install-app united_way || true

echo ""
echo "Running migrations..."
docker compose exec backend bench --site uw.localhost migrate

echo ""
echo "============================================"
echo "Setup complete!"
echo ""
echo "Access:  http://localhost:8080"
echo "Login:   Administrator"
echo "Pass:    admin"
echo ""
echo "Useful commands:"
echo "  docker compose exec backend bench --site uw.localhost migrate"
echo "  docker compose exec backend bench --site uw.localhost console"
echo "  docker compose exec backend bench --site uw.localhost execute united_way.seed.run"
echo "============================================"
