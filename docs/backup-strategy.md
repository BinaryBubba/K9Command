# K9CMD Backup Strategy

## Current Setup

### PostgreSQL — Daily at 2:15am
- Script: `/srv/devshare/myapp/scripts/backup_postgres.sh`
- Output: `/srv/backups/k9command/postgres/myapp_YYYYMMDD_HHMMSS.sql.gz`
- Retention: 14 most recent backups
- Log: `/srv/backups/k9command/postgres/backup.log`

### MinIO — Daily at 3:00am  
- Script: `/srv/devshare/myapp/scripts/backup_minio.sh`
- Output: `/srv/backups/k9command/minio/YYYYMMDD_HHMMSS/`
- Retention: 7 most recent backups
- Log: `/srv/backups/k9command/minio/backup.log`

## Manual Backup Commands

### Postgres
```bash
/srv/devshare/myapp/scripts/backup_postgres.sh
```

### MinIO
```bash
/srv/devshare/myapp/scripts/backup_minio.sh
```

## Restore Postgres from Backup
```bash
# List available backups
ls -lh /srv/backups/k9command/postgres/*.sql.gz

# Restore (WARNING: overwrites current data)
gunzip -c /srv/backups/k9command/postgres/myapp_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i myapp_postgres psql -U myapp myapp
```

## Restore MinIO from Backup
```bash
# List available backups
ls /srv/backups/k9command/minio/

# Restore a bucket
docker cp /srv/backups/k9command/minio/TIMESTAMP/dog-files myapp_minio:/data/
docker exec myapp_minio mc ls local/dog-files
```

## Off-site Backup (Recommended)
Add to crontab for nightly off-site sync:
```bash
# Sync to remote server
0 4 * * * rsync -avz /srv/backups/k9command/ user@backup-server:/backups/k9cmd/
```

## Verify Backups
```bash
# Check recent backups exist
ls -lh /srv/backups/k9command/postgres/ | tail -5
ls -lh /srv/backups/k9command/minio/ | tail -5

# Check backup sizes are reasonable (not 0 bytes)
du -sh /srv/backups/k9command/
```
