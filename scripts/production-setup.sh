#!/bin/bash
# United Way Production Setup Script
# Run this once on a fresh server to set up the production environment.
#
# Prerequisites:
#   - Ubuntu 22.04+ or Debian 12+
#   - Docker and Docker Compose installed
#   - Domain name pointing to this server (for SSL)
#
# Usage: sudo ./production-setup.sh <domain> <admin_password> <db_password>

set -euo pipefail

DOMAIN="${1:-uw.example.com}"
ADMIN_PASSWORD="${2:-changeme}"
DB_PASSWORD="${3:-$(openssl rand -base64 16)}"

echo "=== United Way Production Setup ==="
echo "Domain: ${DOMAIN}"
echo ""

# --- Step 1: Create directory structure ---
echo "[1/7] Creating directory structure..."
mkdir -p /opt/united-way/{secrets,backups,ssl}
cd /opt/united-way

# --- Step 2: Store secrets ---
echo "[2/7] Storing secrets..."
echo "${DB_PASSWORD}" > secrets/db_root_password.txt
chmod 600 secrets/db_root_password.txt

# --- Step 3: Copy compose file ---
echo "[3/7] Setting up Docker Compose..."
# Copy the compose file from the repo
# (Assumes this script is run from the repo root)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "${SCRIPT_DIR}/docker-production.yml" docker-compose.yml

# Update site name in compose file
sed -i "s/uw.localhost/${DOMAIN}/g" docker-compose.yml

# --- Step 4: Start infrastructure ---
echo "[4/7] Starting infrastructure services..."
docker compose up -d mariadb redis-cache redis-queue
echo "Waiting for MariaDB to be ready..."
sleep 30

# --- Step 5: Create site ---
echo "[5/7] Creating Frappe site..."
docker compose up -d backend
sleep 10

docker compose exec backend bench new-site "${DOMAIN}" \
    --mariadb-root-password "${DB_PASSWORD}" \
    --admin-password "${ADMIN_PASSWORD}" \
    --no-mariadb-socket

docker compose exec backend bench --site "${DOMAIN}" install-app united_way
docker compose exec backend bench --site "${DOMAIN}" migrate

# --- Step 6: Load seed data ---
echo "[6/7] Loading seed data..."
docker compose exec backend bench --site "${DOMAIN}" execute united_way.seed.run || true
docker compose exec backend bench --site "${DOMAIN}" execute united_way.setup_dashboard.create_dashboard_elements || true

# --- Step 7: Start all services ---
echo "[7/7] Starting all services..."
docker compose up -d

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Site URL: http://${DOMAIN}"
echo "Admin login: Administrator / ${ADMIN_PASSWORD}"
echo "DB root password: ${DB_PASSWORD} (stored in /opt/united-way/secrets/)"
echo ""
echo "Next steps:"
echo "  1. Set up SSL with certbot or your preferred method"
echo "  2. Configure DNS for ${DOMAIN}"
echo "  3. Set up daily backups: crontab -e"
echo "     0 2 * * * /opt/united-way/backup.sh ${DOMAIN} /opt/united-way/backups"
echo "  4. Configure UW Settings in the admin panel"
echo "  5. Create user accounts and assign roles"
