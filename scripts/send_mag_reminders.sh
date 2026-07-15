#!/usr/bin/env bash
set -Eeuo pipefail

API_URL="https://k9cmd.maniacranch.com/api/meet-and-greets/send-reminders"
CRON_SECRET="$(docker exec myapp_backend printenv CRON_SECRET)"

echo "[$(date --iso-8601=seconds)] Sending meet-and-greet reminders..."

RESPONSE="$(curl -s -w '\nHTTP_STATUS:%{http_code}' -X POST -H "X-Cron-Secret: ${CRON_SECRET}" "${API_URL}")"
HTTP_STATUS="$(echo "${RESPONSE}" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)"
BODY="$(echo "${RESPONSE}" | sed 's/HTTP_STATUS:[0-9]*$//')"

echo "HTTP status: ${HTTP_STATUS}"
echo "Response: ${BODY}"

if [ "${HTTP_STATUS}" != "200" ]; then
    echo "[$(date --iso-8601=seconds)] ERROR: M&G reminder job failed" >&2
    exit 1
fi

echo "[$(date --iso-8601=seconds)] Done."
