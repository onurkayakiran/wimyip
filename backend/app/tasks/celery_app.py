from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init

from app.core.config import settings

celery_app = Celery(
    "ipasn",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)


@worker_process_init.connect
def _ensure_indexes_on_worker_start(**kwargs):
    """worker/beat/ptr-worker container'lari backend'e depends_on ile bagli
    DEGIL; hepsi mongodb hazir olur olmaz calismaya baslayabilir. Bu yuzden
    her worker sureci (backend'in once baslamasina guvenmeden) kendi
    index'lerinin var oldugundan burada emin olur - bu guvensizlik gecmiste
    bir yaris durumunda yinelenen veriye yol acmisti.

    NOT: Bu, Celery'nin worker_process_init sinyali - prefork havuzunda her
    alt surec FORK EDILDIKTEN SONRA bir kez calisir. Bunu modul yuklenirken
    (fork'tan ONCE, ana surecte) cagirmak, pymongo'nun acikca uyardigi
    "MongoClient opened before fork" durumuna yol acardi: forklanan her alt
    surec ana surecin baglantisini miras alir, bu da beklenmedik kilitlenme/
    donma riski tasir. Sinyali kullanarak her alt surec kendi taze
    MongoClient'ini fork SONRASI olusturuyor. (beat sureci fork/worker
    process kullanmadigi icin bu sinyal onda hic tetiklenmez - zaten sadece
    veri yazan worker sureclerinin index garantisine ihtiyaci var.)
    """
    from app.db.indexes import ensure_indexes_sync
    from app.db.sync_client import get_sync_db

    ensure_indexes_sync(get_sync_db())


celery_app.conf.timezone = "UTC"
celery_app.conf.broker_connection_retry_on_startup = True
# PTR taramasi yuksek hacimli oldugu icin ayri bir kuyruga (ve ayri bir
# ptr-worker container'ina) yonlendirilir; diger gorevleri bloklamaz.
celery_app.conf.task_routes = {
    "ingestion.ptr_sweep": {"queue": "ptr"},
    "ingestion.ptr_sweep_country": {"queue": "ptr-country"},
    "ingestion.domain_apex_scan_country": {"queue": "apex-country"},
}
celery_app.conf.beat_schedule = {
    "daily-rir-sync": {
        "task": "ingestion.sync_rir_data",
        "schedule": crontab(hour=3, minute=0),
    },
    "rdap-asn-enrich": {
        "task": "ingestion.rdap_enrich_asns",
        "schedule": settings.rdap_sync_interval_seconds,
    },
    "rdap-prefix-enrich": {
        "task": "ingestion.rdap_enrich_prefixes",
        "schedule": settings.rdap_sync_interval_seconds,
    },
    "bgp-enrich": {
        "task": "ingestion.bgp_enrich",
        "schedule": settings.bgp_sync_interval_seconds,
    },
    "peeringdb-enrich": {
        "task": "ingestion.peeringdb_enrich",
        "schedule": settings.peeringdb_sync_interval_seconds,
    },
    "ct-log-sync": {
        "task": "ingestion.ct_log_sync",
        "schedule": settings.ct_log_sync_interval_seconds,
    },
    "ptr-sweep": {
        "task": "ingestion.ptr_sweep",
        "schedule": settings.ptr_sweep_interval_seconds,
    },
    "ptr-sweep-country": {
        "task": "ingestion.ptr_sweep_country",
        "schedule": settings.country_sweep_interval_seconds,
    },
    "domain-apex-scan-country": {
        "task": "ingestion.domain_apex_scan_country",
        "schedule": settings.apex_country_sweep_interval_seconds,
    },
    "dns-history-sync": {
        "task": "ingestion.dns_history_sync",
        "schedule": settings.dns_history_sync_interval_seconds,
    },
}


@celery_app.task(name="ingestion.sync_rir_data")
def sync_rir_data_task():
    from app.ingestion.rir_sync import sync_all_rirs

    return sync_all_rirs()


@celery_app.task(name="ingestion.rdap_enrich_asns")
def rdap_enrich_asns_task():
    from app.ingestion.rdap_batch import enrich_asns_batch

    return enrich_asns_batch()


@celery_app.task(name="ingestion.rdap_enrich_prefixes")
def rdap_enrich_prefixes_task():
    from app.ingestion.rdap_batch import enrich_prefixes_batch

    return enrich_prefixes_batch()


@celery_app.task(name="ingestion.bgp_enrich")
def bgp_enrich_task():
    from app.ingestion.bgp_batch import enrich_bgp_batch

    return enrich_bgp_batch()


@celery_app.task(name="ingestion.peeringdb_enrich")
def peeringdb_enrich_task():
    from app.ingestion.peeringdb_batch import enrich_peeringdb_batch

    return enrich_peeringdb_batch()


@celery_app.task(name="ingestion.ct_log_sync")
def ct_log_sync_task():
    from app.ingestion.ct_batch import run_ct_sync_batch

    return run_ct_sync_batch()


@celery_app.task(name="ingestion.ptr_sweep")
def ptr_sweep_task():
    from app.ingestion.ptr_batch import run_ptr_sweep_batch

    return run_ptr_sweep_batch()


@celery_app.task(name="ingestion.ptr_sweep_country")
def ptr_sweep_country_task():
    from app.ingestion.ptr_batch import run_ptr_sweep_batch

    return run_ptr_sweep_batch(
        job_name=f"ptr_sweep_country:{settings.target_country}",
        country=settings.target_country,
        batch_size=settings.country_ptr_batch_size,
        rate_limit_seconds=settings.country_ptr_rate_limit_seconds,
    )


@celery_app.task(name="ingestion.domain_apex_scan_country")
def domain_apex_scan_country_task():
    from app.ingestion.domain_apex_batch import run_domain_apex_batch

    return run_domain_apex_batch(
        country=settings.target_country,
        batch_size=settings.apex_country_batch_size,
        domains_per_prefix=settings.apex_country_domains_per_prefix,
        rate_limit_seconds=settings.apex_country_rate_limit_seconds,
    )


@celery_app.task(name="ingestion.dns_history_sync")
def dns_history_sync_task():
    from app.ingestion.dns_history_batch import enrich_dns_history_batch

    return enrich_dns_history_batch()
