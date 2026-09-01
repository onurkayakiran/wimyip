from datetime import datetime, timezone

from bson import ObjectId


def clean_doc(doc: dict) -> dict:
    """Mongo dokumanini JSON-serilestirilebilir hale getirir: ObjectId'leri
    string'e cevirir, naive (tzinfo'suz) datetime'lara UTC tzinfo ekler.

    Motor/PyMongo BSON datetime'lari UTC olarak yazilmis olsa bile naive
    donduruyor - tzinfo eklenmezse jsonable_encoder bunu offset'siz bir ISO
    string'e cevirir, tarayicida `new Date(...)` bunu YEREL saat sanip
    UTC'nin onundeki saat dilimlerinde (orn. TR, UTC+3) yanlis gosterir
    (RemoteWorkersPanel'deki "hep kirmizi gorunme" hatasiyla ayni sinif).
    """
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            doc[k] = str(v)
        elif isinstance(v, datetime) and v.tzinfo is None:
            doc[k] = v.replace(tzinfo=timezone.utc)
        elif isinstance(v, dict):
            doc[k] = {
                kk: (vv.replace(tzinfo=timezone.utc) if isinstance(vv, datetime) and vv.tzinfo is None else vv)
                for kk, vv in v.items()
            }
    return doc
