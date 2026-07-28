import ipaddress
import logging

from pymongo import UpdateOne

from app.db.sync_client import get_sync_db

logger = logging.getLogger(__name__)

BATCH_SIZE = 5000


def backfill_ip_int() -> dict:
    """domain_ip_history'deki (ip_version=4) MEVCUT kayitlara, apex-country
    taramasinin ihtiyac duydugu ip_int alanini geriye donuk doldurur. Tek
    seferlik, elle calistirilir - beat zamanlamasina eklenmez.

    ip_int eksikligini hedefleyen kullanilabilir bir index olmadigi icin
    (bkz. index_defs.py) tum koleksiyonu tek seferlik tarar - ama bu TEKRARLANAN
    yavas sorgular degil, TEK seferlik bir gecis.
    """
    db = get_sync_db()
    updated = 0
    skipped = 0
    ops: list[UpdateOne] = []

    cursor = db.domain_ip_history.find(
        {},
        {"ip": 1, "ip_version": 1, "ip_int": 1},
        no_cursor_timeout=True,
    )
    try:
        for doc in cursor:
            if doc.get("ip_version") != 4 or "ip_int" in doc:
                skipped += 1
                continue
            try:
                ip_int = int(ipaddress.IPv4Address(doc["ip"]))
            except ValueError:
                skipped += 1
                continue

            ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": {"ip_int": ip_int}}))
            if len(ops) >= BATCH_SIZE:
                db.domain_ip_history.bulk_write(ops, ordered=False)
                updated += len(ops)
                logger.info("backfill_ip_int: %s kayit guncellendi (toplam %s)", len(ops), updated)
                ops = []

        if ops:
            db.domain_ip_history.bulk_write(ops, ordered=False)
            updated += len(ops)
    finally:
        cursor.close()

    return {"updated": updated, "skipped": skipped}


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)
    print(json.dumps(backfill_ip_int(), default=str, indent=2))
