#!/bin/sh
set -eu

INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
RETENTION="${BACKUP_RETENTION_COUNT:-7}"

echo "[backup] baslatildi - her ${INTERVAL} saniyede bir yedek alinacak, son ${RETENTION} yedek tutulacak"

# Container her basladiginda (fresh start/restart) script en bastan calisir -
# bu yuzden dogrudan donguye girip hemen backup almak yerine, en son yedekten
# bu yana INTERVAL kadar sure gecmemisse kalan sureyi bekleyip oyle giriyoruz.
# Boylece sik restart (deploy/test sirasinda) gereksiz backup'a yol acmiyor;
# yedek yoksa (ilk kurulum) veya INTERVAL zaten dolmussa (container uzun sure
# kapali kalmis) hemen alinir.
LATEST=$(ls -1t /backups/ipasn_backup_*.archive.gz 2>/dev/null | head -1 || true)
if [ -n "$LATEST" ]; then
  LAST_MTIME=$(stat -c %Y "$LATEST")
  NOW=$(date +%s)
  ELAPSED=$((NOW - LAST_MTIME))
  REMAINING=$((INTERVAL - ELAPSED))
  if [ "$REMAINING" -gt 0 ]; then
    echo "[backup] son yedek ${ELAPSED} sn once alinmis, ${REMAINING} sn sonra devam edilecek"
    sleep "$REMAINING"
  fi
fi

while true; do
  TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
  OUT="/backups/ipasn_backup_${TIMESTAMP}.archive.gz"
  echo "[backup] $(date -u '+%Y-%m-%d %H:%M:%S UTC') yedekleme basliyor: ${OUT}"

  if mongodump \
    --uri="${MONGO_URI}" \
    --db="${MONGO_DB}" \
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
