"""Don't hammer a source that just failed.

A failed request (network down, or the server refusing us — e.g. HTTP 429
"too many requests") is remembered as a marker file next to the cache,
holding the time until which to leave the source alone: `RETRY_AFTER` by
default, or exactly as long as a rate-limited server asked (TNS, for one,
resets its 10-requests-a-minute window in seconds, not hours). Until
then, callers skip the network entirely and fall back to their cached
copy (or report the source unavailable). Without this, every re-plan in
the GUI would retry immediately — exactly the pattern that gets a client
rate-limited or blocked.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

RETRY_AFTER = timedelta(hours=1)


def _marker(cache_path: Path) -> Path:
    return cache_path.with_name(cache_path.name + ".failed")


def recently_failed(cache_path: Path, now: datetime) -> bool:
    """Whether this source is still in its hold-off period."""
    marker = _marker(cache_path)
    try:
        until = datetime.fromisoformat(marker.read_text().strip())
    except OSError:
        return False
    except ValueError:
        # An old-style (empty) marker: hold off `RETRY_AFTER` from its mtime.
        try:
            until = datetime.fromtimestamp(marker.stat().st_mtime, tz=UTC) + RETRY_AFTER
        except OSError:
            return False
    return now < until


def record_failure(
    cache_path: Path, *, hold_off: timedelta | None = None, now: datetime | None = None
) -> None:
    """Hold this source off for `hold_off` (default `RETRY_AFTER`)."""
    until = (now or datetime.now(UTC)) + (hold_off or RETRY_AFTER)
    try:
        marker = _marker(cache_path)
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(until.isoformat())
    except OSError:
        pass  # best-effort — at worst the next call retries


def clear_failure(cache_path: Path) -> None:
    try:
        _marker(cache_path).unlink(missing_ok=True)
    except OSError:
        pass
