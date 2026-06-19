#!/usr/bin/env bash
set -Eeuo pipefail
BACKUP_DIR="/srv/backups/k9command/minio"
CONTAINER_NAME="myapp_minio"
RETENTION_COUNT=7
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "${BACKUP_DIR}"
echo "[$(date --iso-8601=seconds)] Starting MinIO backup..."

# Mirror all buckets to backup directory
docker exec "${CONTAINER_NAME}" mc mirror local/ "/backups/${TIMESTAMP}/" 2>&1 || \
  docker exec "${CONTAINER_NAME}" sh -c "mc mirror local/ /tmp/minio_backup/ && tar -czf /tmp/minio_${TIMESTAMP}.tar.gz /tmp/minio_backup/ && mv /tmp/minio_${TIMESTAMP}.tar.gz /backups/"

# Alternative: copy via docker cp
TEMP_DIR="${BACKUP_DIR}/${TIMESTAMP}"
mkdir -p "${TEMP_DIR}"
for bucket in dog-files vaccination-records incident-photos mag-photos; do
  docker exec "${CONTAINER_NAME}" mc ls "local/${bucket}" > /dev/null 2>&1 && \
    docker cp "${CONTAINER_NAME}:/data/${bucket}" "${TEMP_DIR}/" 2>/dev/null || true
done

echo "[$(date --iso-8601=seconds)] MinIO backup complete: ${TEMP_DIR}"

# Retention
echo "Applying retention: keep newest ${RETENTION_COUNT} backups"
ls -1dt "${BACKUP_DIR}"/[0-9]* 2>/dev/null | tail -n +$((RETENTION_COUNT + 1)) | xargs -r rm -rf

echo "Current backups:"
ls -1dt "${BACKUP_DIR}"/[0-9]* 2>/dev/null || true
echo "[$(date --iso-8601=seconds)] Done."
