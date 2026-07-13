import logging
from datetime import datetime, timezone

import requests
from pymongo import UpdateOne
from pymongo.collection import Collection

from app.db.sync_client import get_sync_db
from app.ingestion.rir_parser import parse_delegated_stats
from app.ingestion.rir_sources import RIR_SOURCES

logger = logging.getLogger(__name__)


def _fetch_lines(url: str) -> list[str]:
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    return resp.text.splitlines()


def _bulk_upsert(
    collection: Collection, docs: list[dict], key_fields: list[str], batch_size: int = 5000
) -> int:
    if not docs:
        return 0
    total = 0
    for i in range(0, len(docs), batch_size):
        batch = docs[i : i + batch_size]
        ops = [
            UpdateOne({k: d[k] for k in key_fields}, {"$set": d}, upsert=True)
            for d in batch
        ]
        result = collection.bulk_write(ops, ordered=False)
        total += result.upserted_count + result.modified_count
    return total


def sync_rir(rir: str, url: str) -> dict:
    db = get_sync_db()
    job_filter = {"job": f"rir_sync:{rir}"}
    db.ingestion_jobs.update_one(
        job_filter,
        {"$set": {"status": "running", "started_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    try:
        lines = _fetch_lines(url)
        prefixes, asns = parse_delegated_stats(rir, lines)
        prefix_count = _bulk_upsert(db.prefixes, prefixes, ["cidr"])
        asn_count = _bulk_upsert(db.asns, asns, ["asn"])
        db.ingestion_jobs.update_one(
            job_filter,
            {
                "$set": {
                    "status": "success",
                    "finished_at": datetime.now(timezone.utc),
                    "prefixes_written": prefix_count,
                    "asns_written": asn_count,
                }
            },
        )
        return {"rir": rir, "prefixes": prefix_count, "asns": asn_count}
    except Exception as exc:
        logger.exception("RIR sync basarisiz: %s", rir)
        db.ingestion_jobs.update_one(
            job_filter,
            {
                "$set": {
                    "status": "failed",
                    "finished_at": datetime.now(timezone.utc),
                    "error": str(exc),
                }
            },
        )
        raise


def sync_all_rirs() -> list[dict]:
    results = []
    for rir, url in RIR_SOURCES.items():
        try:
            results.append(sync_rir(rir, url))
        except Exception as exc:
            results.append({"rir": rir, "error": str(exc)})
    return results


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)
    print(json.dumps(sync_all_rirs(), indent=2))
