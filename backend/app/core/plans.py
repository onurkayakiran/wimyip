from bson import ObjectId

from app.core.config import settings
from app.db.mongo import get_db

# Free/Premium plan yardimcilari - hem monitors.py (monitor limiti) hem
# scans.py (IP Tarama erisimi + limiti) tarafindan paylasiliyor.


async def get_user_plan(user_id: str) -> str:
    user = await get_db().users.find_one({"_id": ObjectId(user_id)}, {"plan": 1})
    return (user or {}).get("plan", "free")


def max_monitors_for_plan(plan: str) -> int:
    return settings.premium_max_monitors if plan == "premium" else settings.free_max_monitors
