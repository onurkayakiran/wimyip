# remote-worker

Uzak bir sunucuya deploy edilen, merkezdeki `remote-api` servisiyle dar
yetkili bir HTTP API üzerinden konuşan tek amaçlı worker. Bu klasördeki
container ne Mongo'ya ne Redis'e ne de merkezdeki `control`/Docker socket'e
hiçbir zaman erişemez — sadece kendi `REMOTE_API_TOKEN`'ıyla
`CENTRAL_API_URL`'e outbound HTTPS isteği atar, hiçbir inbound port açmaz.

## Kurulum

1. `/admin` panelinden ("Uzak Workerlar" bölümü) bu lokasyon için bir
   etiket + izinli kuyruk seçerek yeni bir token üretin. Token sadece o an
   gösterilir, bir daha görüntülenemez — kopyalayıp güvenli saklayın.
2. `.env.example`'ı `.env` olarak kopyalayıp `CENTRAL_API_URL` ve
   `REMOTE_API_TOKEN` alanlarını doldurun.
3. `docker compose up -d --build`

## Merkez tarafında gereken (bu repo dışında)

`remote-api` merkezi `docker-compose.yml`'de `REMOTE_API_PORT` (varsayılan
8001) ile host'ta yayınlanır. Bunun internete güvenli (TLS ile) açılması
için host-nginx/Cloudflare tarafında yeni bir subdomain (örn.
`remote-api.<domain>` → `127.0.0.1:8001`) tanımlanması gerekir — bu adım
repo'daki `frontend/nginx.conf`'un da belirttiği gibi sunucu seviyesinde,
version kontrolü dışında yönetiliyor.

## Bir token'ı iptal etmek

Bir lokasyonun ele geçirildiğinden şüpheleniyorsanız, `/admin` panelinden
o token'ı iptal edin — bir sonraki istekte worker anında 401 alır ve tüm
erişimi kesilir. O lokasyonun katkıları `domains.sources` alanında
`remote:<etiket>` ile işaretlendiği için ayrıca tespit/temizlenebilir.
