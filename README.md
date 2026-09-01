# IP / ASN / Domain Arşivi

Dünya genelindeki IP bloklarını, ASN sahiplik bilgilerini ve bu bloklar üzerinde
çalışan domainlerin (IP, nameserver ve nameserver IP) geçmişini arşivleyen
self-hosted, tamamen Docker üzerinde çalışan bir araç.

## Hızlı Başlangıç

Bu proje kendi MongoDB'sini çalıştırmaz — harici (kendi sunucunuz, Atlas
veya başka bir yönetilen servis) bir MongoDB'ye bağlanır.

```bash
cp .env.example .env       # MONGO_URI'yi kendi MongoDB sunucunuza göre doldurun
docker compose up -d --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/health

### Harici MongoDB Bağlantısı

`.env` içindeki `MONGO_URI` tam bağlantı string'i olarak girilir, örn.:

```bash
MONGO_URI=mongodb://kullanici:sifre@mongo-sunucunuz:27017/ipasn?authSource=admin
```

Hedef sunucuda bu kullanıcı ve `MONGO_DB` ile aynı isimdeki veritabanı
(veya en azından o kullanıcının yazma yetkisi) önceden oluşturulmuş
olmalı — bu proje `MONGO_INITDB_ROOT_*` ile otomatik kullanıcı/veritabanı
oluşturmaz, sadece bağlanır. Koleksiyonlar ve index'ler ilk yazımda
uygulama tarafından otomatik oluşturulur (bkz. `backend/app/db/index_defs.py`).

## RIR verisini manuel senkronize etme

```bash
docker compose exec backend python -m app.ingestion.rir_sync
```

Bu komut ARIN/RIPE/APNIC/LACNIC/AFRINIC'in delegated-extended istatistik
dosyalarını çekip `prefixes` ve `asns` koleksiyonlarını doldurur. Aynı görev
`beat` servisi tarafından her gün 03:00 UTC'de otomatik olarak da çalıştırılır.

## Whois (RDAP) sahiplik geçmişi

Her ASN/prefix için ilgili RIR'ın RDAP servisinden organizasyon bilgisi
çekilir, ham yanıt `whois_snapshots`'a arşivlenir ve organizasyon adı/handle
değiştiğinde `asn_org_history` / `prefix_org_history`'ye yeni bir dönem
eklenir (değişmediyse sadece `last_seen` güncellenir). Bu şekilde zaman
içinde sahiplik değişiklikleri arşivlenmiş olur.

```bash
# Tek bir ASN/prefix için anlık sorgulama + arşivleme
curl -X POST http://localhost:8001/api/asns/15169/refresh
curl -X POST http://localhost:8001/api/prefixes/8.8.8.0/24/refresh

# Geçmişi görüntüleme
curl http://localhost:8001/api/asns/15169/history
curl http://localhost:8001/api/prefixes/8.8.8.0/24/history
```

`beat` servisi, tüm `asns`/`prefixes` koleksiyonunu RIR sunucularına saygılı
bir hızda (varsayılan: saniyede 1 istek, her 5 dakikada bir 100'lük batch)
kalınan yerden devam ederek sürekli tarar ve zenginleştirir — ilerleme
`ingestion_jobs` koleksiyonunda cursor olarak tutulur, konteyner yeniden
başlasa da kaldığı yerden devam eder.

## BGP geçmişi (RIPEstat) + PeeringDB

RIPEstat'ın `announced-prefixes` API'si üzerinden her ASN'in geçmişte ve şu
an duyurduğu prefixler zaman aralıklarıyla çekilir; `prefix_asn_history`
koleksiyonuna işlenir. `/api/lookup/ip/{ip}` artık RIR tahsis bilgisinin
yanında bu BGP geçmişini de (`bgp` alanı) döndürür. PeeringDB'den de ağın
kendi beyan ettiği operatör/organizasyon profili (`asn_peeringdb_info`)
çekilir.

```bash
curl -X POST http://localhost:8001/api/asns/15169/refresh-bgp
curl http://localhost:8001/api/asns/15169/prefixes
curl -X POST http://localhost:8001/api/asns/15169/refresh-peeringdb
curl http://localhost:8001/api/asns/15169/peeringdb
```

`beat` servisi bu iki kaynağı da (RDAP'a ek olarak) her 5 dakikada bir,
kaldığı yerden devam eden hız-sınırlı batch'lerle otomatik tarar.

## Domain keşfi (CT log + PTR taraması)

İki bağımsız kaynaktan sürekli domain keşfi yapılır:

- **Certificate Transparency**: crt.sh'nin herkese açık Postgres veritabanı
  üzerinden yeni sertifikalar (`ct_log_entry` cursor'ı ile) tespit edilir,
  ham sertifika kendi tarafımızda parse edilerek domain adları (SAN + CN)
  çıkarılır. `beat` her 2 dakikada bir kaldığı yerden devam eder.
- **PTR (reverse DNS) taraması**: kendi Unbound resolver container'ımız
  (`unbound`) üzerinden, sadece gerçekten tahsis edilmiş (allocated) IP
  bloklarını hedef alan, hız sınırlı ve devam edilebilir bir tarama. Yüksek
  hacmi nedeniyle ayrı bir Celery kuyruğunda (`ptr-worker` container'ı)
  çalışır ve diğer görevleri bloklamaz.

```bash
curl "http://localhost:8001/api/domains?q=google"
curl http://localhost:8001/api/domains/one.one.one.one
curl http://localhost:8001/api/lookup/ip/1.0.0.1   # artik PTR kaydini da icerir
```

PTR taraması dünya IPv4 uzayının sadece tahsis edilmiş kısmını (~3+ milyar
adres) kapsar ve bilinçli olarak yavaş/nazik bir hızda ilerler (varsayılan:
saniyede ~10 sorgu) — bu, sürekli çalışan ve zamanla büyüyen bir arşiv
sürecidir, "bitmesi" beklenmez. Hızı `PTR_RATE_LIMIT_SECONDS` /
`PTR_BATCH_SIZE` ortam değişkenleriyle ayarlayabilirsiniz.

## DNS geçmişi (domain IP + nameserver geçmişi)

Bilinen her domain için A/AAAA/NS kayıtları periyodik olarak yeniden
çözümlenir (kendi Unbound resolver'ımız üzerinden). Her gözlemlenen değer
(IP veya nameserver) kendi `first_seen`/`last_seen` çiftiyle ayrı bir satır
olarak saklanır — yani domain başka bir IP'ye taşınsa bile eski kayıt
silinmez, sadece yeni bir satır eklenir. Ayrıca her nameserver'ın **kendi**
IP adresi de ayrıca izlenir (nameserver'lar da zamanla IP değiştirebilir).

```bash
curl -X POST http://localhost:8001/api/domains/google.com/refresh-dns
curl http://localhost:8001/api/domains/google.com/history        # IP + NS gecmisi
curl http://localhost:8001/api/nameservers/ns1.google.com/history # nameserver'in kendi IP gecmisi
curl http://localhost:8001/api/nameservers/ns1.google.com/domains # bu nameserver'i kullanan domainler
```

`/api/lookup/ip/{ip}` artık tam çemberi kapatıyor: RIR tahsisi + BGP
duyuru geçmişi + PTR kaydı + (eğer bu IP bir nameserver'sa) hangi
domainlere hizmet verdiği, hepsi tek bir sorguda.

## Servisleri elle yeniden başlatma

```bash
./scripts/restart.sh                        # tüm servisleri restart et (rebuild yok)
./scripts/restart.sh backend                 # sadece backend'i restart et
./scripts/restart.sh backend worker beat     # birden fazla servisi restart et
./scripts/restart.sh --build                 # tüm servisleri yeniden derleyip restart et
./scripts/restart.sh --build backend worker  # sadece bunları yeniden derleyip restart et
```

Servis adları: `redis`, `backend`, `worker`, `beat`, `unbound`,
`ptr-worker`, `ptr-worker-country`, `apex-worker-country`, `frontend`,
`remote-api`. Kod değişikliği yaptıysanız `--build` kullanın; sadece bir
servisi (örn. takılı kalmış bir görevi) yeniden başlatmak için düz haliyle
yeterli.

## Arka plan görevlerini izleme

Ana sayfadaki "Arka Plan Görevleri" paneli 20 saniyede bir kendini
yeniler ve her görev için yeşil/kırmızı bir durum noktası gösterir.
Bir görev şu durumlarda kırmızı işaretlenir:

- Beklenen zamanlamasına göre çok uzun süredir güncellenmediyse (örn.
  1 dakikada bir çalışması gereken PTR taraması 10 dakikadır sessizse)
- Son çalıştığında `status: "error"` ile tamamen başarısız olduysa
  (örn. dış servise hiç ulaşılamadıysa) — bu durumda `last_error` alanında
  hata mesajı da görünür
- Son batch'inin %90'ından fazlası tek tek başarısız olduysa (örn. DNS
  resolver'a ulaşılamıyorsa, her IP kendi içinde "failed" sayılır ama
  görev genel olarak "ok" dönebilir — bu oran bunu da yakalar)

Aynı bilgi `GET /api/status` üzerinden de alınabilir (`healthy_count`/
`total_count` özeti + her görev için `healthy`/`stale`/`last_error`).
Container'ların kendisi çökerse (`docker compose ps` ile görülür) Docker
`restart: unless-stopped` politikasıyla otomatik olarak yeniden başlatılır;
tek tük görev hataları için ayrıca `docker compose logs -f worker beat
ptr-worker` ile canlı log takip edilebilir.

## Frontend

React + Vite tabanlı çok sayfalı arayüz (http://localhost:3001):

- **Ana sayfa**: istatistikler + arka plan görevlerinin (RIR/RDAP/BGP/PeeringDB/CT-log/PTR/DNS) canlı durumu
- **Birleşik arama çubuğu** (her sayfanın üstünde): girilen değeri otomatik algılar
  - `1.2.3.4` → IP sayfası, `1.2.3.0/24` → Prefix sayfası, `AS15169`/`15169` → ASN sayfası,
    `google.com` → Domain sayfası, diğer her şey → organizasyon adına göre arama sonuçları
- **IP sayfası**: RIR tahsisi + BGP duyuru geçmişi + PTR kaydı + (nameserver'sa) hizmet verdiği domainler
- **Prefix sayfası**: RIR tahsisi + RDAP sahiplik geçmişi ("Şimdi Sorgula" ile anlık tetiklenebilir). BGP'de görülen ama RIR tablosunda birebir karşılığı olmayan daha spesifik alt-prefixler için otomatik olarak içinde bulunduğu RIR bloğuna düşer.
- **ASN sayfası**: RIR + RDAP geçmişi + PeeringDB profili + BGP duyurulan prefixler (hepsi ayrı ayrı "Şimdi Sorgula" ile anlık tetiklenebilir)
- **Domain sayfası**: A/AAAA + NS geçmiş zaman çizelgesi, PTR bağlantıları, "DNS Şimdi Sorgula"
- **Nameserver sayfası**: nameserver'ın kendi IP geçmişi + hizmet verdiği domainler

## Mimari ve yol haritası

Bkz. [PLAN.md](PLAN.md).
