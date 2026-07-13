#!/usr/bin/env bash
# Servisleri elle yeniden baslatmak icin kisayol.
#
# Kullanim:
#   ./scripts/restart.sh                        # tum servisleri restart et (rebuild YOK)
#   ./scripts/restart.sh backend                 # sadece backend'i restart et
#   ./scripts/restart.sh backend worker beat      # birden fazla servisi restart et
#   ./scripts/restart.sh --build                 # tum servisleri yeniden derleyip restart et
#   ./scripts/restart.sh --build backend worker   # sadece bunlari yeniden derleyip restart et
#
# Servisler: mongodb, redis, backend, worker, beat, unbound, ptr-worker,
#            frontend, backup
set -euo pipefail

cd "$(dirname "$0")/.."

BUILD=false
if [ "${1:-}" = "--build" ]; then
  BUILD=true
  shift
fi

SERVICES=("$@")

if [ "$BUILD" = true ]; then
  if [ ${#SERVICES[@]} -eq 0 ]; then
    echo "Tüm servisler yeniden derleniyor ve başlatılıyor..."
    docker compose build
    docker compose up -d
  else
    echo "Yeniden derleniyor ve başlatılıyor: ${SERVICES[*]}"
    docker compose build "${SERVICES[@]}"
    docker compose up -d "${SERVICES[@]}"
  fi
else
  if [ ${#SERVICES[@]} -eq 0 ]; then
    echo "Tüm servisler yeniden başlatılıyor..."
    docker compose restart
  else
    echo "Yeniden başlatılıyor: ${SERVICES[*]}"
    docker compose restart "${SERVICES[@]}"
  fi
fi

echo ""
docker compose ps --format 'table {{.Name}}\t{{.Status}}'
