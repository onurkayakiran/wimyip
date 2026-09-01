from pydantic import BaseModel

# `items`/`results` kuyruk tipine gore farkli sekle sahip (PTR: {ip}; DNS
# history: {domain, ips, nameservers, mx, txt}) - bu yuzden burada sabit bir
# alan seti yerine genel dict kullanilir, sekil kontrolu ilgili
# queues/<isim>.py::apply() icinde yapilir.


class ClaimResponse(BaseModel):
    batch_id: str | None
    queue: str
    items: list[dict]
    lease_seconds: int
    # Is-tabanli kuyruklar (orn. port_scan) icin batch'in tum ogelerinin
    # paylastigi konfigurasyon (port listesi, IP'ler arasi gecikme vb.) -
    # surekli-tarama kuyruklari (ptr_sweep/dns_history/dns_history_apex) None
    # doner, davranislari degismez.
    meta: dict | None = None


class SubmitRequest(BaseModel):
    batch_id: str
    queue: str
    results: list[dict]


class SubmitResponse(BaseModel):
    accepted: bool
    written: int
    found: int
