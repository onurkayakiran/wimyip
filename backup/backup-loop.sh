#!/bin/sh
set -eu

INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
RETENTION="${BACKUP_RETENTION_COUNT:-7}"

echo "[backup] baslatildi - her ${INTERVAL} saniyede bir yedek alinacak, son ${RETENTION} yedek tutulacak"

while true; do
  TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
  OUT="/backups/ipasn_backup_${TIMESTAMP}.archive.gz"
  echo "[backup] $(date -u '+%Y-%m-%d %H:%M:%S UTC') yedekleme basliyor: ${OUT}"

  if mongodump \
    --uri="mongodb://${MONGO_ROOT_USER}:${MONGO_ROOT_PASSWORD}@mongodb:27017/${MONGO_DB}?authSource=admin" \
    --archive --gzip >"${OUT}"; then
    echo "[backup] tamamlandi: ${OUT} ($(du -h "${OUT}" | cut -f1))"
    # en yeni RETENTION kadar yedegi birakip gerisini sil
    ls -1t /backups/ipasn_backup_*.archive.gz 2>/dev/null | tail -n "+$((RETENTION + 1))" | xargs -r rm -f
  else
    echo "[backup] BASARISIZ oldu, yarim kalan dosya siliniyor"
    rm -f "${OUT}"
  fi

  sleep "${INTERVAL}"
done
