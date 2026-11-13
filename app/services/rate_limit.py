"""Simple in-process rate limiter and daily cap.

Keeps a per-IP sliding window plus a global daily counter. State is in
memory only — fine for a single-process deployment.
"""
import time
import threading
from collections import defaultdict, deque
from datetime import date

from app.config import get_settings


_lock = threading.Lock()
_per_ip_hits: dict[str, deque[float]] = defaultdict(deque)
_daily_count = 0
_daily_date: date | None = None


class RateLimitExceeded(Exception):
    pass


def check_and_record(client_ip: str) -> None:
    """Raise RateLimitExceeded when over the per-IP or daily cap."""
    global _daily_count, _daily_date
    settings = get_settings()
    now = time.time()
    today = date.today()
    window_seconds = 3600

    with _lock:
        if _daily_date != today:
            _daily_date = today
            _daily_count = 0

        if _daily_count >= settings.daily_cap:
            raise RateLimitExceeded(
                "Yikes, looks like we're out of credits for today. Come back tomorrow!"
            )

        hits = _per_ip_hits[client_ip]
        cutoff = now - window_seconds
        while hits and hits[0] < cutoff:
            hits.popleft()

        if len(hits) >= settings.rate_limit_per_hour:
            raise RateLimitExceeded(
                f"Whoah there partner, we're glad you like our product but to keep this free for everyone you're limited to {settings.rate_limit_per_hour} searches per hour. Come back soon!"
            )

        hits.append(now)
        _daily_count += 1
