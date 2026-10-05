from slowapi import Limiter
from slowapi.util import get_remote_address

from soukk_backend.settings.appSettings import settings

# Counters live in Redis so every worker and every container shares them.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.rate_limit_storage_url,
    # Like a moving window (no double burst at the minute boundary) but only
    # two small counters per key instead of one entry per request.
    strategy="sliding-window-counter",
    key_prefix="ratelimit",
    # If Redis is unreachable, keep limiting per process instead of failing
    # requests; slowapi switches back once Redis answers again.
    in_memory_fallback_enabled=True,
    # slowapi talks to Redis with blocking calls on the event loop, so a Redis
    # that hangs would freeze every request. Give up after 1 second instead; the
    # failure switches the limiter to the in-memory fallback above.
    storage_options={"socket_connect_timeout": 1, "socket_timeout": 1},
)
