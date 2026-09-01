from datetime import datetime, timezone

from app.db.sync_client import get_sync_db


def refresh_stats_cache() -> dict:
    db = get_sync_db()
    counts = {
        "prefixes": db.prefixes.estimated_document_count(),
        "asns": db.asns.estimated_document_count(),
        "domains": db.domains.estimated_document_count(),
    }
    db.stats_cache.update_one(
        {"_id": "counts"},
        {"$set": {**counts, "updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return counts
