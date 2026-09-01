from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # NOT: bilhassa env_file YOK - docker-compose.yml bu servise sadece
    # asagidaki alanlari acikca veriyor, .env'deki ADMIN_PASSWORD/
    # CONTROL_SERVICE_TOKEN/CELERY_BROKER_URL gibi sirlar bu container'in
    # ortamina hic girmiyor.
    mongo_uri: str = ""
    mongo_db: str = "ipasn"
    max_batch_size: int = 1000
    claim_lease_seconds: int = 300
    rate_limit_claim_per_minute: int = 20
    rate_limit_submit_per_minute: int = 20
    # port_scan (SYN tarama) is-tabanli, cok daha uzun surebilir - lease bu
    # sureyi kapsamali, aksi halde apply() sonuclari "batch suresi dolmus"
    # diye reddeder. Digger kuyruklar claim_lease_seconds'i kullanmaya devam
    # ediyor (bkz. queues/port_scan.py::LEASE_SECONDS).
    port_scan_lease_seconds: int = 21600

    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()
