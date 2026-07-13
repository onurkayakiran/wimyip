# Proje Planı — IP / ASN / Domain Arşivi

Bu dosya projenin fazlarını ve ilerleme durumunu takip eder. Tam mimari
detayları için konuşma geçmişindeki plana bakılabilir; burada sadece
faz/görev checklist'i tutulur. Her madde tamamlandıkça işaretlenir.

## Faz 1 — İskelet
- [x] docker-compose.yml (mongodb, redis, backend, worker, beat, frontend)
- [x] .env.example / .gitignore
- [x] Backend iskeleti (FastAPI + health endpoint)
- [x] Frontend iskeleti (React + Vite + nginx)
- [x] Taşınabilirlik: scripts/backup.sh, scripts/restore.sh

## Faz 2 — RIR Ingestion
- [x] RIR delegated-extended parser (IPv4 + ASN)
- [x] Mongo upsert (prefixes, asns koleksiyonları + index'ler)
- [x] Celery task + günlük beat zamanlaması
- [x] API: /api/prefixes, /api/asns, /api/lookup/ip/{ip}, /api/stats
- [x] Frontend: dashboard sayacı + IP arama

## Faz 3 — RDAP Whois + Sahiplik Geçmişi
- [x] RDAP sorgu istemcisi (her RIR'in RDAP servisine dogrudan sorgu, org bilgisi cikarma)
- [x] whois_snapshots koleksiyonu (ham RDAP JSON arşivi)
- [x] asn_org_history + prefix_org_history diff mantığı (sahiplik değişim arşivi)
- [x] Hız-sınırlı, devam edilebilir (cursor tabanlı) arka plan zenginleştirme görevi (beat: her 5 dakikada bir)
- [x] API: GET /api/asns/{asn}/history, POST /api/asns/{asn}/refresh, GET /api/prefixes/{cidr}/history, POST /api/prefixes/{cidr}/refresh

## Faz 4 — BGP (RIPEstat) + PeeringDB
- [x] RIPEstat announced-prefixes entegrasyonu (ASN başına geçmiş+güncel duyurulan prefixler, zaman aralıklarıyla)
- [x] prefix_asn_history koleksiyonu (güncel + geçmiş ASN↔prefix eşlemesi, IP lookup'a entegre)
- [x] PeeringDB org zenginleştirme (net + org detayı, asn_peeringdb_info)
- [x] Ortak resumable batch runner (batch_runner.py) — RDAP/BGP/PeeringDB tarafından paylaşılıyor
- [x] API: GET /api/asns/{asn}/prefixes, /peeringdb, POST .../refresh-bgp, .../refresh-peeringdb; /api/lookup/ip/{ip} artık BGP bilgisini de içeriyor

## Faz 5 — Domain Keşfi
- [x] Certificate Transparency log kesfi — crt.sh'nin herkese acik Postgres DB'si uzerinden (`ct_log_entry` cursor + ham sertifikayi kendimiz parse ediyoruz, cunku `certificate_identity` toplu taramaya kapatilmis). **Not:** Plandaki "ct-listener" websocket/streaming servisi yerine Celery beat uzerinde periyodik (2 dakikada bir) resumable poller olarak kuruldu — guvenilir ucretsiz bir gercek-zamanli CT stream servisi kalmadigi icin bu, aym sonucu (surekli buyuyen domain arsivi) daha saglam bir mekanizmayla veriyor.
- [x] PTR sweep worker — kendi Unbound resolver container'imiz (`unbound`) uzerinden, ayri Celery kuyrugunda (`ptr-worker`), hiz-sinirli ve checkpoint'li (sadece allocated RIR bloklarini tarar)
- [x] domains koleksiyonu (hem ct_log hem ptr kaynaklarini `sources` alaninda birlikte tutuyor)
- [x] API: GET /api/domains, /api/domains/{domain}; /api/lookup/ip/{ip} artik PTR kaydini da iceriyor

## Faz 6 — DNS Geçmiş Takibi
- [x] dns_history_sync periyodik görevi (bilinen domainler için A/AAAA/NS yeniden çözümleme, kendi Unbound resolver'imiz uzerinden, resumable cursor ile)
- [x] domain_ip_history / domain_ns_history güncelleme mantığı (her gozlemlenen deger kendi first_seen/last_seen'iyle ayri satir, gecmis hic ezilmiyor)
- [x] nameserver_ip_history — her NS hostname'inin KENDI A/AAAA kaydinin ayri gecmisi
- [x] API: GET/POST /api/domains/{domain}/history|refresh-dns, GET /api/nameservers/{ns}/history|domains
- [x] /api/lookup/ip/{ip} artik "bu IP bir nameserver ise hangi domainlere hizmet veriyor" bilgisini de iceriyor (tam cember: RIR + BGP + PTR + nameserver-domain baglantisi tek sorguda)

## Faz 7 — Frontend Genişletme
- [x] React Router ile çok sayfalı yapı (Home, IP, Prefix, ASN, Domain, Nameserver, Search)
- [x] Prefix detay sayfası (RIR + RDAP sahiplik geçmişi; BGP'de gorulen ama RIR'da tam eslesmeyen alt-prefixler icin otomatik en-dar-kapsayan-blok fallback'i)
- [x] ASN detay sayfası (RIR + RDAP gecmisi + PeeringDB profili + BGP duyurulan prefixler, hepsi "Şimdi Sorgula" ile anlik tetiklenebilir)
- [x] Domain detay sayfası (IP + NS geçmişi zaman çizelgesi, PTR baglantilari, "DNS Şimdi Sorgula")
- [x] Nameserver detay sayfası (kendi IP geçmişi + hizmet verdiği domainler)
- [x] Birleşik arama (IP/CIDR/ASN/domain istemci tarafinda pattern-tespitiyle doğrudan yönlendirme; org adı için backend /api/search)
- [x] Dashboard'a arka plan görev durumu (ingestion_jobs) paneli eklendi
- [x] Backend API: GET /api/search, GET /api/status
- [x] Gerçek tarayıcıda (Playwright) uçtan uca doğrulandı: dashboard → ASN → prefix (BGP alt-prefix fallback dahil) → domain → nameserver → IP, konsol hatasız. Bu sırada iki gerçek veri tutarlılığı hatası bulunup düzeltildi: (1) BGP'nin gördüğü spesifik prefixler RIR tablosunda tam eşleşmiyordu, (2) refresh-dns ile manuel sorgulanan domainler `domains` ana koleksiyonuna hiç yazılmıyordu.
- [x] Arka plan görevleri için dashboard'da canlı sağlık göstergesi (🟢/🔴, 20 sn'de bir yenilenir); `unbound`'u bilerek durdurup PTR taramasının %90+ hata oranını yakaladığını doğruladım (önceden bu durum sessizce "ok" görünüyordu)
- [x] IP sayfasına "BGP Verisini Şimdi Topla" butonu — RIPEstat'ın prefix-overview'ı ile o an duyuran ASN'i canlı bulup tam geçmişini tarıyor (daha önce hiç BGP verisi olmayan bir IP için bile çalışır, çünkü hangi ASN'in sorgulanacağını kendisi keşfediyor)
- [x] crt.sh'nin replica veritabanindan gelen gecici "recovery conflict" hatalari icin otomatik yeniden deneme (taze baglantiyla, 3 deneme)
- [x] **Altyapi duzeltmesi:** nginx `proxy_pass`'i backend'in Docker IP'sini kalici onbelleklemesi, backend her yeniden olusturuldugunda (rebuild/restart) frontend'de 502 hatasina yol aciyordu. `resolver 127.0.0.11 valid=10s` + degiskenli proxy_pass ile backend her yeniden basladiginda frontend'e dokunmadan otomatik toparlanacak sekilde duzeltildi ve gercek senaryoyla (backend'i yeniden olusturup) dogrulandi.
- [x] **Veri bütünlüğü düzeltmesi:** `worker`/`beat`/`ptr-worker` container'ları `backend`'e `depends_on` ile bağlı olmadığı için, backend henüz index'lerini kurmadan bu süreçler yazmaya başlayabiliyordu — bu yarış durumu `nameserver_ip_history`'de gerçek yinelenen kayıtlara ve birkaç koleksiyonda index'in hiç kurulamamasına yol açmıştı (restore sırasında fark edildi). Index tanımları `index_defs.py`'da tek yerde toplandı, her index ayrı try/except ile korunacak şekilde `indexes.py`'a taşındı, ve artık her Celery süreci (worker/beat/ptr-worker) kendi başlangıcında (backend'den bağımsız) kendi index'lerini garanti ediyor. Var olan yinelenen kayıtlar temizlendi, tam yedek/geri-yükle round-trip'i hatasız doğrulandı.
- [x] **Yedekleme:** `backup` servisi (docker-compose) `docker compose up -d` ile otomatik başlıyor, varsayılan 24 saatte bir `mongodump` alıp son 7 yedeği tutuyor (named volume'de, macOS'un Desktop-klasörü izin kısıtına takılmamak için host bind-mount kullanmıyor). `scripts/export_backups.sh` (docker cp ile host'a çıkarır), `scripts/backup.sh` (anlık, doğrudan host'a), `scripts/restore.sh`/`restore_latest.sh` (geri yükleme) — hepsi gerçek veriyle (261k+ prefix, 427k+ toplam doküman) uçtan uca test edildi.
- [x] `scripts/restart.sh` — servisleri elle (tekil/coklu/hepsi, gerekirse `--build` ile) yeniden baslatma kisayolu.
- [x] **Pymongo fork-safety düzeltmesi:** `ensure_indexes_sync()`'in Celery modülü yüklenirken (fork'tan ÖNCE, ana süreçte) çağrılması "MongoClient opened before fork" riskine yol açıyordu (forklanan alt süreçler ana sürecin bağlantısını miras alır, kilitlenme riski). `worker_process_init` sinyaline taşındı (her forklanan alt süreç kendi bağlantısını fork SONRASI kurar). Bu değişiklik yeni bir yarış durumu ortaya çıkardı (birden fazla alt süreç aynı index'i aynı anda kurmaya çalışıp çakışıyordu) — `indexes.py` artık "önce dene, çakışırsa index zaten var mı kontrol et, yoksa backoff ile tekrar dene" mantığıyla bu yarışa dayanıklı. `worker` servisinin concurrency'si de (varsayılan host CPU sayısı, örn. 14) 2'ye sabitlendi.
- [x] **Güvenlik iyileştirmesi:** backend/worker/beat/ptr-worker artık root yerine ayrıcalıksız `appuser` (uid 1000) olarak çalışıyor. **Ek düzeltme:** appuser'a geçiş `/app`'in sahipliğini değiştirmediği için `beat` kendi zamanlama dosyasını (`celerybeat-schedule`) yazamayıp sürekli çöküyordu (hiçbir periyodik görev tetiklenmiyordu) — Dockerfile'da `chown -R appuser:appuser /app` ile düzeltildi.
- [x] **Worker concurrency düzeltmesi:** aynı kuyrukta 6 farklı periyodik görev (rdap-asn, rdap-prefix, bgp, peeringdb, ct-log, dns-history) olduğu için concurrency=2 yetersiz kaldı — sık çalışan (2 dk) ct-log görevi sürekli slot kapatıp 5 dk'lık diğer görevlerin saatlerce aç kalmasına yol açtı. 6'ya çıkarıldı (index çakışması ayrıca çözüldüğü için artık yüksek concurrency güvenli).
- [x] **Fiziksel sunucu uyumluluğu:** mongo:5.0+ CPU'da AVX desteği zorunlu kılar, AVX'i olmayan eski sunucularda `mongod` "Illegal instruction" ile çöküyor. `MONGO_IMAGE_TAG` ortam değişkeniyle yapılandırılabilir hale getirildi (varsayılan `7`, AVX'siz makinelerde `.env`'de `4.4` yapılır — bu projede 5.0+'a özgü hiçbir özellik kullanılmadığı için tam uyumlu). Healthcheck hem `mongosh` (7+) hem eski `mongo` (4.4) kabuğuyla çalışacak şekilde güncellendi. `backup` servisinin image'ı da aynı etikete göre build ediliyor (build arg).
- [x] **CT log senkronu self-healing:** cursor, crt.sh'nin (birden fazla replica'dan yanıt veren) güncel maksimumundan 1M+ ID geride kaldığı halde sürekli 0 sonuç dönerse (gözlemlenen gerçek senaryo: taşınan bir ortamda cursor kalıcı olarak sıkışmıştı), artık otomatik olarak "şimdi"ye yakın bir noktaya atlıyor — bir daha sessizce sonsuza kadar takılı kalamaz.
- [x] **Sertifika ayrıştırma dayanıklılığı:** eski/standart-dışı bir sertifikanın bozuk ASN.1 alanı `cryptography` kütüphanesinin katı ayrıştırıcısını kırıp TÜM batch'i (500 sertifikanın 499'u dahil) düşürüyordu — `_extract_domains` artık tüm ayrıştırma+extension erişimini tek try/except ile sarıyor, tek bozuk sertifika sessizce atlanıyor.
