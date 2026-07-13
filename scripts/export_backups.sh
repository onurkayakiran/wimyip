#!/usr/bin/env bash
# backup servisinin ic named volume'unda biriken otomatik yedekleri
# host'taki ./backups klasorune cikarir (docker cp kullanir, bind-mount
# gerektirmez).
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p backups

CONTAINER=$(docker compose ps -q backup)
if [ -z "$CONTAINER" ]; then
  echo "backup container'ı çalışmıyor. Önce 'docker compose up -d backup' çalıştırın."
  exit 1
fi

BEFORE=$(ls backups/*.archive.gz 2>/dev/null | wc -l | tr -d ' ')
docker cp "${CONTAINER}:/backups/." ./backups/
AFTER=$(ls backups/*.archive.gz 2>/dev/null | wc -l | tr -d ' ')

echo "Yedekler ./backups/ altına çıkarıldı (toplam ${AFTER} dosya, önceden ${BEFORE})."
ls -lh backups/*.archive.gz 2>/dev/null | tail -5
