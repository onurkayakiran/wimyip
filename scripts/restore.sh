#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -z "${1:-}" ]; then
  echo "Kullanım: $0 <backup-dosyasi.archive.gz>"
  exit 1
fi

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

docker compose exec -T mongodb mongorestore \
  --username "${MONGO_ROOT_USER}" \
  --password "${MONGO_ROOT_PASSWORD}" \
  --authenticationDatabase admin \
  --db "${MONGO_DB}" \
  --archive --gzip --drop < "$1"

echo "Geri yükleme tamamlandı."
