#!/bin/bash
# United Way Frappe Backup Script
# Run daily via cron: 0 2 * * * /path/to/backup.sh
#
# Usage: ./backup.sh [site_name] [backup_dir]

set -euo pipefail

SITE="${1:-uw.localhost}"
BACKUP_DIR="${2:-/backups/united_way}"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30
BENCH_DIR="${BENCH_DIR:-/home/frappe/frappe-bench}"

echo "=== United Way Backup: ${DATE} ==="

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# --- Step 1: Frappe site backup (DB + files) ---
echo "[1/4] Running bench backup..."
cd "${BENCH_DIR}"
bench --site "${SITE}" backup --with-files

# Find the latest backup files
BACKUP_PATH="${BENCH_DIR}/sites/${SITE}/private/backups"
LATEST_DB=$(ls -t "${BACKUP_PATH}"/*database*.sql.gz 2>/dev/null | head -1)
LATEST_FILES=$(ls -t "${BACKUP_PATH}"/*files*.tar 2>/dev/null | head -1)
LATEST_PRIVATE=$(ls -t "${BACKUP_PATH}"/*private-files*.tar 2>/dev/null | head -1)

# --- Step 2: Copy to backup location ---
echo "[2/4] Copying backups to ${BACKUP_DIR}..."
DEST="${BACKUP_DIR}/${DATE}"
mkdir -p "${DEST}"

if [ -n "${LATEST_DB}" ]; then
    cp "${LATEST_DB}" "${DEST}/"
    echo "  Database: $(basename "${LATEST_DB}")"
fi

if [ -n "${LATEST_FILES}" ]; then
    cp "${LATEST_FILES}" "${DEST}/"
    echo "  Public files: $(basename "${LATEST_FILES}")"
fi

if [ -n "${LATEST_PRIVATE}" ]; then
    cp "${LATEST_PRIVATE}" "${DEST}/"
    echo "  Private files: $(basename "${LATEST_PRIVATE}")"
fi

# --- Step 3: Backup site config ---
echo "[3/4] Backing up site config..."
cp "${BENCH_DIR}/sites/${SITE}/site_config.json" "${DEST}/site_config.json"
cp "${BENCH_DIR}/sites/common_site_config.json" "${DEST}/common_site_config.json" 2>/dev/null || true

# --- Step 4: Cleanup old backups ---
echo "[4/4] Cleaning up backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -type d -mtime +${RETENTION_DAYS} -exec rm -rf {} + 2>/dev/null || true

# Clean up bench's own backups (keep last 3)
cd "${BACKUP_PATH}" 2>/dev/null && ls -t *database*.sql.gz | tail -n +4 | xargs rm -f 2>/dev/null || true
cd "${BACKUP_PATH}" 2>/dev/null && ls -t *files*.tar | tail -n +4 | xargs rm -f 2>/dev/null || true

echo ""
echo "=== Backup complete ==="
echo "Location: ${DEST}"
du -sh "${DEST}" 2>/dev/null || true
