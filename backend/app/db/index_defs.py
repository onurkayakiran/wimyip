# Tum koleksiyonlarin index tanimlari tek bir yerde tutulur; hem FastAPI'nin
# async (motor) baslangic kancasi hem de Celery worker/beat/ptr-worker
# surecklerinin senkron (pymongo) baslangic kancasi buradan besleniyor.
#
# ONEMLI: worker/beat/ptr-worker container'lari backend'e depends_on ile bagli
# DEGIL - hepsi mongodb hazir olur olmaz paralel calismaya baslayabilir. Daha
# once index olusturma islemi SADECE backend'in FastAPI lifespan'inde
# yapiliyordu; bu da backend henuz index'i olusturmadan worker'in ayni
# (alan1, alan2) ciftine iki kez yazip TEKIL index kurulmadan yinelenen kayit
# birakabilecegi bir yaris durumu yaratti (gercekte oldu, nameserver_ip_history
# koleksiyonunda). Artik her sureç kendi index'lerini kendisi garanti ediyor.
#
from app.core.config import settings

# Her eleman: (collection_name, keys, kwargs)
INDEX_DEFS: list[tuple[str, object, dict]] = [
    ("prefixes", "cidr", {"unique": True}),
    ("prefixes", [("start_ip", 1), ("end_ip", 1)], {}),
    ("prefixes", "rir", {}),
    ("prefixes", "country", {}),
    (
        "prefixes",
        [("country", 1), ("version", 1), ("start_ip", 1), ("end_ip", 1)],
        {},
    ),
    ("asns", "asn", {"unique": True}),
    ("asns", "rir", {}),
    ("asns", "country", {}),
    ("domains", "domain", {"unique": True}),
    ("domains", "sources", {}),
    ("domain_ip_history", [("domain", 1), ("ip", 1)], {"unique": True}),
    ("domain_ip_history", "ip_int", {}),
    ("domain_ns_history", [("domain", 1), ("nameserver", 1)], {"unique": True}),
    ("domain_ns_history", "nameserver", {}),
    ("nameserver_ip_history", [("nameserver", 1), ("ip", 1)], {"unique": True}),
    ("nameserver_ip_history", "ip", {}),
    ("domain_mx_history", [("domain", 1), ("exchange", 1)], {"unique": True}),
    ("domain_txt_history", [("domain", 1), ("value_hash", 1)], {"unique": True}),
    ("ptr_records", [("ip", 1), ("ptr_hostname", 1)], {"unique": True}),
    ("ptr_records", "ip", {}),
    (
        "whois_snapshots",
        [("object_type", 1), ("object_key", 1), ("fetched_at", -1)],
        {},
    ),
    ("asn_org_history", [("asn", 1), ("first_seen", 1)], {}),
    (
        "asn_peering_history",
        [("asn", 1), ("neighbour_asn", 1), ("direction", 1)],
        {"unique": True},
    ),
    ("asn_peering_history", "neighbour_asn", {}),
    ("prefix_org_history", [("cidr", 1), ("first_seen", 1)], {}),
    ("prefix_asn_history", [("prefix", 1), ("asn", 1)], {"unique": True}),
    ("prefix_asn_history", [("start_ip", 1), ("end_ip", 1)], {}),
    ("prefix_asn_history", "asn", {}),
    ("asn_peeringdb_info", "asn", {"unique": True}),
    ("ingestion_jobs", "job", {"unique": True}),
    # Uzak (remote) worker API - bkz. remote-api/ ve remote-worker/
    ("remote_worker_tokens", "token_hash", {"unique": True}),
    ("remote_worker_status", [("token_id", 1), ("queue", 1)], {"unique": True}),
    # Admin panelden tetiklenen SYN port taramasi - bkz. remote-api/app/queues/port_scan.py
    ("port_scan_jobs", "status", {}),
    ("port_scan_jobs", "created_at", {}),
    ("port_scan_results", [("job_id", 1), ("ip", 1)], {"unique": True}),
    ("port_scan_results", "ip_int", {}),
    # Kullanici paneli + domain monitoring (HTTP/HTTPS/Ping)
    ("users", "username", {"unique": True}),
    ("users", "email", {"unique": True}),
    ("monitors", [("user_id", 1), ("target", 1)], {"unique": True}),
    ("monitors", "next_check_at", {}),
    ("monitor_results", [("monitor_id", 1), ("checked_at", -1)], {}),
    # TTL index: monitor_result_retention_days sonra otomatik silinir -
    # domains koleksiyonunun sinirsiz buyumesiyle yasanan performans
    # sorununu (bkz. PLAN.md) bastan onlemek icin.
    (
        "monitor_results",
        "checked_at",
        {"expireAfterSeconds": settings.monitor_result_retention_days * 86400},
    ),
]
