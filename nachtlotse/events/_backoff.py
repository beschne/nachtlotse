"""Don't hammer a source that just failed.

A failed request (network down, or the server refusing us — e.g. HTTP 429
"too many requests") is remembered as a marker file next to the cache; for
`RETRY_AFTER` after it, callers skip the network entirely and fall back to
their cached copy (or report the source unavailable). Without this, every
re-plan in the GUI would retry immediately — exactly the pattern that gets
a client rate-limited or blocked.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

RETRY_AFTER = timedelta(hours=1)


def _marker(cache_path: Path) -> Path:
    return cache_path.with_name(cache_path.name + ".failed")


def recently_failed(cache_path: Path, now: datetime) -> bool:
    """Whether a request for this cache file failed within `RETRY_AFTER`."""
    try:
        failed_at = datetime.fromtimestamp(_marker(cache_path).stat().st_mtime, tz=UTC)
    except OSError:
        return False
    return now - failed_at < RETRY_AFTER


def record_failure(cache_path: Path) -> None:
    try:
        marker = _marker(cache_path)
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
    except OSError:
        pass  # best-effort — at worst the next call retries


def clear_failure(cache_path: Path) -> None:
    try:
        _marker(cache_path).unlink(missing_ok=True)
    except OSError:
        pass
