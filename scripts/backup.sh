#!/bin/bash
# UK Tax Residency Day Tracker - Backup Script
# Safely backs up SQLite database and evidence vault.
#
# Usage: ./scripts/backup.sh [backup_dir]
# Default backup dir: /opt/daytracker/backups

set -euo pipefail

BACKUP_DIR="${1:-/opt/daytracker/backups}"
DATE=$(date +%Y%m%d_%H%M%S)
DATA_DIR="/opt/daytracker/data"
VAULT_DIR="/opt/daytracker/vault"
DB_FILE="${DATA_DIR}/daytracker.db"

# For local dev, use relative paths if /opt/daytracker doesn't exist
if [ ! -d "$DATA_DIR" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    DATA_DIR="${PROJECT_DIR}/data"
    VAULT_DIR="${PROJECT_DIR}/vault"
    DB_FILE="${DATA_DIR}/daytracker.db"
    BACKUP_DIR="${PROJECT_DIR}/backups"
fi

mkdir -p "$BACKUP_DIR"

echo "=== DayTracker Backup ==="
echo "Date: $DATE"
echo "Backup dir: $BACKUP_DIR"

# 1. Safe SQLite backup (using .backup command for consistency)
if [ -f "$DB_FILE" ]; then
    echo "Backing up database..."
    sqlite3 "$DB_FILE" ".backup '${BACKUP_DIR}/daytracker_${DATE}.db'"
    echo "  -> ${BACKUP_DIR}/daytracker_${DATE}.db"
else
    echo "WARNING: Database file not found at $DB_FILE"
fi

# 2. Archive vault directory
if [ -d "$VAULT_DIR" ] && [ "$(ls -A $VAULT_DIR 2>/dev/null)" ]; then
    echo "Archiving vault..."
    tar czf "${BACKUP_DIR}/vault_${DATE}.tar.gz" -C "$(dirname $VAULT_DIR)" "$(basename $VAULT_DIR)/"
    echo "  -> ${BACKUP_DIR}/vault_${DATE}.tar.gz"
else
    echo "INFO: Vault directory empty or not found, skipping."
fi

# 3. Cleanup old backups (keep 30 days)
echo "Cleaning up backups older than 30 days..."
find "$BACKUP_DIR" -type f -mtime +30 -delete 2>/dev/null || true

echo "=== Backup complete ==="

# Summary
echo ""
echo "Backup files:"
ls -lh "${BACKUP_DIR}/"*"${DATE}"* 2>/dev/null || echo "  (none created)"
