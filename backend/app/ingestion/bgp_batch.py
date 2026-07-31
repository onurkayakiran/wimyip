import logging

from app.core.config import settings
from app.ingestion.batch_runner import run_resumable_batch
from app.ingestion.bgp_sync import sync_asn_announcements, sync_asn_peering

logger = logging.getLogger(__name__)


def enrich_bgp_batch() -> dict:
    def fetch_page(db, cursor):
        query = {"asn": {"$gt": cursor}} if cursor is not None else {}
        return list(
            db.asns.find(query, {"asn": 1}).sort("asn", 1).limit(settings.ripestat_batch_size)
        )

    def process_one(doc):
        sync_asn_announcements(doc["asn"])
        sync_asn_peering(doc["asn"])

    return run_resumable_batch(
        "bgp_sync:asns",
        fetch_page,
        process_one,
        lambda doc: doc["asn"],
        settings.ripestat_rate_limit_seconds,
    )


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO)
    print(json.dumps(enrich_bgp_batch(), default=str, indent=2))
