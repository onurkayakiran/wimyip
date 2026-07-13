#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

LATEST=$(ls -t backups/ipasn_backup_*.archive.gz 2>/dev/null | head -1 || true)

if [ -z "$LATEST" ]; then
  echo "backups/ altında hiç yedek bulunamadı."
  exit 1
fi

echo "En güncel yedek geri yükleniyor: $LATEST"
./scripts/restore.sh "$LATEST"
