"""The one HTTP GET every events client shares — a separate seam so tests
can patch `urllib.request.urlopen` once for all of them."""

from __future__ import annotations

import urllib.error
import urllib.request

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
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise EventsUnavailable(f"{source} request failed: {exc}") from exc
