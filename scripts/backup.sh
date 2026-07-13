#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"
OUT_FILE="$BACKUP_DIR/ipasn_backup_${TIMESTAMP}.archive.gz"

docker compose exec -T mongodb mongodump \
  --username "${MONGO_ROOT_USER}" \
  --password "${MONGO_ROOT_PASSWORD}" \
  --authenticationDatabase admin \
  --db "${MONGO_DB}" \
  --archive --gzip > "$OUT_FILE"

echo "Yedek oluşturuldu: $OUT_FILE"
