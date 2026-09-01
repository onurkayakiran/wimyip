import time
from collections import defaultdict, deque

from fastapi import HTTPException

# Token basina, tek-replika icin yeterli basit bellek-ici rate limit. remote-api
# birden fazla replika ile calistirilirsa bu sayac paylasilmaz - bu bilinen bir
# sinirlama (Redis'e kasitli olarak baglanmiyoruz, bkz. plan).
_windows: dict[str, deque] = defaultdict(deque)


def enforce_rate_limit(key: str, limit_per_minute: int) -> None:
    now = time.monotonic()
    window = _windows[key]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= limit_per_minute:
        raise HTTPException(status_code=429, detail="Cok fazla istek, biraz yavaslatin")
    window.append(now)
