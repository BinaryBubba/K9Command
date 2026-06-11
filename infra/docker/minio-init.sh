#!/bin/sh
# Wait for MinIO to be ready then set bucket policies
sleep 5
mc alias set local http://myapp_minio:9000 k9cmd_minio 'K9cmd_MinIO_2024!'
mc mb --ignore-existing local/dog-files
mc mb --ignore-existing local/vaccination-records
mc mb --ignore-existing local/incident-photos
mc mb --ignore-existing local/mag-photos
mc anonymous set download local/dog-files
mc anonymous set download local/vaccination-records
mc anonymous set download local/mag-photos
echo "MinIO buckets initialized"
