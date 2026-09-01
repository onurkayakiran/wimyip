#!/usr/bin/env python3
"""Herhangi bir koleksiyonda, verilen key alan(lar)ina gore duplicate
dokumanlari TEK dokumanda birlestirir - restore sonrasi unique index
kurulmasini engelleyen E11000 hatalarini gidermek icin genel amacli script
(dedupe_domains.py'nin domains'e ozel olmayan genellemesi).

Hangi kayit "kazanir" (kalir): updated_at/finished_at/synced_at/last_seen/
scanned_at/created_at alanlarindan hangisi varsa ona gore EN YENI olan;
hicbiri yoksa ilk bulunan doguman. Digerleri (varsa alanlari) kazanan
uzerine BIRLESTIRILMEZ, sadece silinir - bu script domains'teki gibi
"sources birlestir" mantigina sahip degil, cunku genelde bu tur (cursor/
durum tutan) koleksiyonlarda "en son durum gecerlidir" mantigi dogru olan.

Calistirma (COLLECTION ve KEYS ortam degiskenleriyle, virgulle birden fazla
key alani verilebilir - bilesik unique index'ler icin):
    docker compose run --rm -T -e DEDUPE_COLLECTION=ingestion_jobs -e DEDUPE_KEYS=job \\
        backend python - < scripts/dedupe_collection.py

Idempotent'tir - duplicate kalmayana kadar tekrar tekrar calistirilabilir.
"""
import json
import logging
import os

from pymongo import MongoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("dedupe_collection")

_TIMESTAMP_FIELDS = ("updated_at", "finished_at", "synced_at", "last_seen", "scanned_at", "created_at")


def _sort_key(doc: dict):
    # Datetime nesnelerini DOGRUDAN karsilastirmiyoruz (naive/aware karisimi
    # TypeError firlatabilir) - str() ile karsilastirilabilir bir forma
    # ceviriyoruz. Zaman damgasi olmayan dokumanlar en dusuk oncelikli.
    for f in _TIMESTAMP_FIELDS:
        if doc.get(f):
            return (1, str(doc[f]))
    return (0, "")


def main() -> dict:
    collection_name = os.environ["DEDUPE_COLLECTION"]
    keys = [k.strip() for k in os.environ["DEDUPE_KEYS"].split(",") if k.strip()]
    db = MongoClient(os.environ["MONGO_URI"])[os.environ.get("MONGO_DB", "ipasn")]
    coll = db[collection_name]

    group_id = {k: f"${k}" for k in keys}
    pipeline = [
        {"$group": {"_id": group_id, "count": {"$sum": 1}, "doc_ids": {"$push": "$_id"}}},
        {"$match": {"count": {"$gt": 1}}},
    ]
    cursor = coll.aggregate(pipeline, allowDiskUse=True, batchSize=50)

    groups_found = 0
    docs_removed = 0
    for group in cursor:
        doc_ids = group["doc_ids"]
        docs = list(coll.find({"_id": {"$in": doc_ids}}))
        docs.sort(key=_sort_key, reverse=True)
        remove_ids = [d["_id"] for d in docs[1:]]
        if remove_ids:
            result = coll.delete_many({"_id": {"$in": remove_ids}})
            docs_removed += result.deleted_count
        groups_found += 1

        if groups_found % 100 == 0:
            logger.info("%s grup islendi, %s kayit silindi", groups_found, docs_removed)

    return {
        "collection": collection_name,
        "keys": keys,
        "duplicate_groups": groups_found,
        "docs_removed": docs_removed,
    }


if __name__ == "__main__":
    print(json.dumps(main(), default=str, indent=2))
