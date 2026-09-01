from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017/ipasn"
    mongo_db: str = "ipasn"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    # RDAP zenginlestirme: RIR sunucularina saygili, hiz-sinirli, devam
    # edilebilir arka plan taramasi icin ayarlar
    rdap_rate_limit_seconds: float = 1.0
    rdap_batch_size: int = 100
    rdap_sync_interval_seconds: float = 300.0

    ripestat_rate_limit_seconds: float = 0.5
    ripestat_batch_size: int = 50
    bgp_sync_interval_seconds: float = 300.0

    peeringdb_rate_limit_seconds: float = 1.0
    peeringdb_batch_size: int = 100
    peeringdb_sync_interval_seconds: float = 300.0

    # Certificate Transparency log tabanli domain kesfi (crt.sh uzerinden,
    # ct_log_entry tablosunu cursor olarak kullanir). crt.sh herkese acik,
    # PAYLASILAN bir kaynak - burayi cok agresif ayarlamak crt.sh'yi
    # zorlayabilir/bizi engellenmeye maruz birakabilir, olculu artirin.
    ct_batch_size: int = 500
    ct_log_sync_interval_seconds: float = 120.0

    # PTR (reverse DNS) taramasi: kendi Unbound resolver container'imiz
    # uzerinden, hiz-sinirli, devam edilebilir. Bu KENDI kaynagimiz oldugu
    # icin CT log'a gore cok daha rahat hizlandirilabilir.
    ptr_resolver_host: str = "unbound"
    ptr_rate_limit_seconds: float = 0.1
    ptr_batch_size: int = 500
    ptr_sweep_interval_seconds: float = 60.0

    # Ulke bazli PTR taramasi (ayri container: ptr-worker-country). Global
    # sweep'ten tamamen bagimsiz kendi cursor'unu tutar (job adi
    # "ptr_sweep_country:<target_country>"), boylece birbirlerine karismazlar.
    target_country: str = "TR"
    country_ptr_batch_size: int = 500
    country_ptr_rate_limit_seconds: float = 0.1
    country_sweep_interval_seconds: float = 60.0

    # Ulke bazli APEX (ana, subdomain olmayan) domain taramasi (ayri
    # container: apex-worker-country). domain_ip_history'de zaten bilinen,
    # target_country'ye tahsisli IP'lerde barinan domainlerden sadece apex
    # olanlari icin sync_domain_dns'i tetikler.
    apex_country_batch_size: int = 50
    apex_country_domains_per_prefix: int = 200
    apex_country_rate_limit_seconds: float = 0.2
    apex_country_sweep_interval_seconds: float = 120.0

    # Bilinen domainler icin A/AAAA/NS + nameserver IP gecmisini periyodik
    # olarak yeniden dogrulayan tarama
    dns_history_rate_limit_seconds: float = 0.2
    dns_history_batch_size: int = 100
    dns_history_sync_interval_seconds: float = 300.0

    # /admin sayfasi: uzak worker/token yonetimi, IP subnet taramasi vb.
    admin_password: str = ""

    # Anasayfa istatistik sayaclarini (prefixes/asns/domains) periyodik
    # olarak onbellege alan gorev - domains 16M+ oldugu icin canli
    # count_documents({}) her istekte tam tarama yapip 504'e yol aciyordu.
    stats_refresh_interval_seconds: float = 300.0

    # IP Subnet taramasi (SYN port scan, worker-portscan container'i
    # uzerinden - bkz. remote-api/app/queues/port_scan.py). Artik admin-only
    # DEGIL, sadece "premium" plandaki kullanicilara acik (bkz.
    # backend/app/api/routes/scans.py). portscan_max_hosts: yanlislikla cok
    # genis bir blok (orn. /16) taratilmasini onleyen guvenlik siniri.
    # max_active_scans_per_user: bir kullanicinin ayni anda kuyrukta/calisir
    # durumda tutabilecegi en fazla is sayisi - kotuye kullanimi sinirlamak
    # icin (tek basina yeterli degil ama savunmanin bir katmani).
    portscan_default_delay_seconds: float = 5.0
    portscan_max_hosts: int = 256
    max_active_scans_per_user: int = 3

    # Kullanici paneli (kayit/giris) - JWT tabanli, cookie/session DEGIL
    # (Authorization: Bearer header, mevcut CORS allow_origins=["*"] ile
    # cookie tabanli bir semaya gore cok daha basit/uyumlu). Mutlaka
    # degistirin - varsayilan deger sadece yerel gelistirme icin.
    jwt_secret: str = "change_me_please"
    jwt_expire_minutes: int = 10080  # 7 gun, tek access token, refresh yok

    # Domain monitoring (HTTP/HTTPS/Ping) - kullanici basina kaynak
    # tuketimini sinirlamak icin plan bazli (free/premium) limitler.
    # Admin bu degerleri (ve premium'a kimin gectigini) k8s ConfigMap/.env
    # uzerinden ayarlar - bkz. /admin/users/{id}/plan.
    free_max_monitors: int = 5
    premium_max_monitors: int = 100
    min_monitor_interval_seconds: int = 60
    default_monitor_interval_seconds: int = 300
    monitor_check_batch_size: int = 50
    monitor_check_tick_seconds: float = 30.0
    monitor_http_timeout_seconds: float = 10.0
    monitor_ping_timeout_seconds: float = 5.0
    # Bir monitor sonucu bu kadar gun sonra otomatik silinir (TTL index) -
    # domains koleksiyonunun sinirsiz buyumesiyle yasanan performans
    # sorununu (bkz. PLAN.md) burada bastan onlemek icin.
    monitor_result_retention_days: int = 30

    # Durum degisiminde (up->down / down->up) e-posta bildirimi icin SMTP.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_address: str = ""
    smtp_use_tls: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
