#!/bin/bash
# United Way Frappe Restore Script
# Usage: ./restore.sh <backup_directory> [site_name]

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_directory> [site_name]"
    echo "Example: $0 /backups/united_way/20260222_020000"
    exit 1
fi

BACKUP_DIR="$1"
SITE="${2:-uw.localhost}"
BENCH_DIR="${BENCH_DIR:-/home/frappe/frappe-bench}"

echo "=== United Way Restore ==="
echo "Source: ${BACKUP_DIR}"
echo "Site: ${SITE}"

# Verify backup exists
if [ ! -d "${BACKUP_DIR}" ]; then
    echo "ERROR: Backup directory not found: ${BACKUP_DIR}"
    exit 1
fi

DB_BACKUP=$(ls "${BACKUP_DIR}"/*database*.sql.gz 2>/dev/null | head -1)
FILES_BACKUP=$(ls "${BACKUP_DIR}"/*files*.tar 2>/dev/null | head -1)
PRIVATE_BACKUP=$(ls "${BACKUP_DIR}"/*private-files*.tar 2>/dev/null | head -1)

if [ -z "${DB_BACKUP}" ]; then
    echo "ERROR: No database backup found in ${BACKUP_DIR}"
    exit 1
fi

echo ""
echo "Database: $(basename "${DB_BACKUP}")"
[ -n "${FILES_BACKUP}" ] && echo "Files: $(basename "${FILES_BACKUP}")"
[ -n "${PRIVATE_BACKUP}" ] && echo "Private: $(basename "${PRIVATE_BACKUP}")"
echo ""

read -p "Proceed with restore? This will OVERWRITE the current site data. (y/N) " confirm
if [ "${confirm}" != "y" ] && [ "${confirm}" != "Y" ]; then
    echo "Aborted."
    exit 0
fi

cd "${BENCH_DIR}"

# Build restore command
RESTORE_CMD="bench --site ${SITE} restore ${DB_BACKUP}"
[ -n "${FILES_BACKUP}" ] && RESTORE_CMD="${RESTORE_CMD} --with-public-files ${FILES_BACKUP}"
[ -n "${PRIVATE_BACKUP}" ] && RESTORE_CMD="${RESTORE_CMD} --with-private-files ${PRIVATE_BACKUP}"

echo "Running restore..."
eval "${RESTORE_CMD}"

# Run migrate to apply any pending schema changes
echo "Running migrate..."
bench --site "${SITE}" migrate

echo "Clearing cache..."
bench --site "${SITE}" clear-cache

echo ""
echo "=== Restore complete ==="
