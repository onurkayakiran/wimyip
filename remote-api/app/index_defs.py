# backend/app/db/index_defs.py ile ayni desen - her surec kendi index'ini
# kendisi garanti eder (bkz. o dosyadaki gerekce notu).
#
# Her eleman: (collection_name, keys, kwargs)
INDEX_DEFS: list[tuple[str, object, dict]] = [
    ("remote_worker_tokens", "token_hash", {"unique": True}),
    ("remote_worker_status", [("token_id", 1), ("queue", 1)], {"unique": True}),
    ("remote_batches", "token_id", {}),
    ("remote_batches", [("queue", 1), ("status", 1)], {}),
    # claimed_at uzerinde TTL - tamamlanmis/terk edilmis batch kayitlari 7 gun
    # sonra otomatik silinir, ayri bir temizlik gorevi gerekmez.
    ("remote_batches", "claimed_at", {"expireAfterSeconds": 604800}),
    # port_scan (SYN tarama) is-tabanli kuyrugu - bkz. queues/port_scan.py.
    # TTL YOK: bunlar arsivlenen bulgular, gecici claim defteri degil.
    ("port_scan_jobs", "status", {}),
    ("port_scan_jobs", "created_at", {}),
    ("port_scan_results", [("job_id", 1), ("ip", 1)], {"unique": True}),
    ("port_scan_results", "ip_int", {}),
]
