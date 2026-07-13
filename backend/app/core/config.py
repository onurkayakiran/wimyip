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

    # Bilinen domainler icin A/AAAA/NS + nameserver IP gecmisini periyodik
    # olarak yeniden dogrulayan tarama
    dns_history_rate_limit_seconds: float = 0.2
    dns_history_batch_size: int = 100
    dns_history_sync_interval_seconds: float = 300.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
