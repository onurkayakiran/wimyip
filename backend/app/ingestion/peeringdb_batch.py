import logging

from app.core.config import settings
from app.ingestion.batch_runner import run_resumable_batch
from app.ingestion.peeringdb_sync import sync_asn_peeringdb

logger = logging.getLogger(__name__)


def enrich_peeringdb_batch() -> dict:
    def fetch_page(db, cursor):
        query = {"asn": {"$gt": cursor}} if cursor is not None else {}
        return list(
            db.asns.find(query, {"asn": 1}).sort("asn", 1).limit(settings.peeringdb_batch_size)
        )

    def process_one(doc):
        sync_asn_peeringdb(doc["asn"])

    return run_resumable_batch(
        "peeringdb_sync:asns",
        fetch_page,
        process_one,
        lambda doc: doc["asn"],
        settings.peeringdb_rate_limit_seconds,
    )


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)
    print(json.dumps(enrich_peeringdb_batch(), default=str, indent=2))
