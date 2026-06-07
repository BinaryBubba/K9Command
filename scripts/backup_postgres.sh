#!/usr/bin/env bash
set -Eeuo pipefail

BACKUP_DIR="/srv/backups/k9command/postgres"
CONTAINER_NAME="myapp_postgres"
DB_NAME="myapp"
DB_USER="myapp"
RETENTION_COUNT=14

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"
TMP_FILE="${OUT_FILE}.tmp"

mkdir -p "${BACKUP_DIR}"

echo "[$(date --iso-8601=seconds)] Starting Postgres backup..."
echo "Container: ${CONTAINER_NAME}"
echo "Database:  ${DB_NAME}"
echo "Output:    ${OUT_FILE}"

docker exec "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" \
  | gzip -9 > "${TMP_FILE}"

mv "${TMP_FILE}" "${OUT_FILE}"

echo "[$(date --iso-8601=seconds)] Backup complete."

echo "Applying retention policy: keep newest ${RETENTION_COUNT} backups"
ls -1t "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | tail -n +$((RETENTION_COUNT + 1)) | xargs -r rm -f

echo "Current backups:"
ls -1th "${BACKUP_DIR}"/*.sql.gz 2>/dev/null || true

echo "[$(date --iso-8601=seconds)] Done."
