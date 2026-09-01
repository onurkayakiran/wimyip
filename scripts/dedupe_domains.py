#!/usr/bin/env python3
"""domains koleksiyonunda ayni 'domain' degerine sahip birden fazla dokuman
varsa (restore sonrasi unique index kurulmasini engelliyor), hepsini TEK bir
dokumanda birlestirir: en erken first_seen, en gec last_seen, sources
dizilerinin birlesimi. Diger collection'lar 'domain' STRING'ine referans
veriyor (domains._id'ye degil), bu yuzden fazlalik dokumanlari silmek
guvenli - hicbir yerde kirik referans birakmaz.

Calistirma (backend image'i icinde, index-build tetiklemeden):
    docker compose run --rm -T backend python - < scripts/dedupe_domains.py

Idempotent'tir - duplicate kalmayana kadar tekrar tekrar calistirilabilir.
"""
import json
import logging
import os

from pymongo import MongoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("dedupe_domains")


def main() -> dict:
    db = MongoClient(os.environ["MONGO_URI"])[os.environ.get("MONGO_DB", "ipasn")]
    groups_found = 0
    docs_removed = 0

    pipeline = [
        {"$group": {"_id": "$domain", "count": {"$sum": 1}, "doc_ids": {"$push": "$_id"}}},
        {"$match": {"count": {"$gt": 1}}},
    ]
    cursor = db.domains.aggregate(pipeline, allowDiskUse=True, batchSize=50)

    for group in cursor:
        doc_ids = group["doc_ids"]
        docs = list(db.domains.find({"_id": {"$in": doc_ids}}))

        first_seens = [d["first_seen"] for d in docs if d.get("first_seen")]
        last_seens = [d["last_seen"] for d in docs if d.get("last_seen")]
        sources = sorted({s for d in docs for s in (d.get("sources") or [])})

        update: dict = {}
        if first_seens:
            update["first_seen"] = min(first_seens)
        if last_seens:
            update["last_seen"] = max(last_seens)
        if sources:
            update["sources"] = sources

        survivor_id = doc_ids[0]
        if update:
            db.domains.update_one({"_id": survivor_id}, {"$set": update})

        remove_ids = [i for i in doc_ids if i != survivor_id]
        result = db.domains.delete_many({"_id": {"$in": remove_ids}})
        docs_removed += result.deleted_count
        groups_found += 1

        if groups_found % 500 == 0:
            logger.info("%s grup islendi, %s kayit silindi", groups_found, docs_removed)

    return {"duplicate_groups": groups_found, "docs_removed": docs_removed}


if __name__ == "__main__":
    print(json.dumps(main(), default=str, indent=2))
