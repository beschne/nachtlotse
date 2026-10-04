"""The one HTTP GET every events client shares — a separate seam so tests
can patch `urllib.request.urlopen` once for all of them."""

from __future__ import annotations

import urllib.error
import urllib.request
from datetime import timedelta

from nachtlotse.events import EventsUnavailable

_TIMEOUT_S = 30.0
_USER_AGENT = "Nachtlotse (astrophotography session planner)"


def get(url: str, *, source: str) -> bytes:
    """GET `url`; any network/HTTP failure becomes `EventsUnavailable`
    naming `source`."""
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_S) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise EventsUnavailable(
            f"{source} request failed: {exc}", retry_after=_retry_after(exc)
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise EventsUnavailable(f"{source} request failed: {exc}") from exc


def _retry_after(exc: urllib.error.HTTPError) -> timedelta | None:
    """How long a rate-limited server asked us to wait: TNS sends
    `x-rate-limit-reset` (seconds until its window resets), others the
    standard `Retry-After` (seconds). None if neither is usable."""
    if exc.code != 429 or exc.headers is None:
        return None
    for header in ("x-rate-limit-reset", "Retry-After"):
        value = exc.headers.get(header)
        try:
            return timedelta(seconds=max(1.0, float(value)))
        except (TypeError, ValueError):
            continue
    return None
