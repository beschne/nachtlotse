"""Sky-survey cutouts for the framing preview — CDS hips2fits client.

An optional backdrop, the same kind of layer as `weather/`: it shows what
the sky around a target actually looks like (including the orientation of
elongated objects, which the catalog doesn't record), but never feeds a
number into the engine. Every framing value still comes from
`engine.framing_preview`; without network or cache the preview simply
draws without an image.

Images are requested in the convention `engine.framing_preview` uses for
its offsets: gnomonic (TAN) projection, ICRS, north up, east left. They're
square and sized by `cutout_fov_deg` so a frame rotated to any angle stays
inside. The sky doesn't change, so cached cutouts never expire.
"""

from __future__ import annotations

import hashlib
import math
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

_API_URL = "https://alasky.cds.unistra.fr/hips-image-services/hips2fits"
# A cutout takes a few seconds server-side (~4 s observed for a 1024 px
# DSS2 color field).
_TIMEOUT_S = 30.0

DEFAULT_SURVEY = "CDS/P/DSS2/color"
# Attribution to print on any rendered image that uses a cutout.
SURVEY_CREDITS: dict[str, str] = {
    DEFAULT_SURVEY: "DSS2 color (STScI/CDS) via CDS hips2fits",
}
DEFAULT_SIZE_PX = 1024
DEFAULT_CACHE_DIR = Path(".cache/sky_survey")

# Extra room around the frame's diagonal, so the rotated frame never
# touches the image edge and neighbors just outside it stay in view.
_FIELD_MARGIN = 1.15

_JPEG_MAGIC = b"\xff\xd8\xff"


class SurveyImageUnavailable(Exception):
    """A cutout couldn't be fetched — network, HTTP, or not an image.

    Routine, not exceptional: callers fall back to the drawn preview
    without a backdrop.
    """


@dataclass(frozen=True)
class SurveyImage:
    """A square cutout, north up, east left, centered on (ra, dec)."""

    jpeg_bytes: bytes
    center_ra_deg: float
    center_dec_deg: float
    fov_deg: float
    size_px: int
    survey: str

    @property
    def credit(self) -> str:
        return SURVEY_CREDITS.get(self.survey, self.survey)

    @property
    def arcmin_per_px(self) -> float:
        return self.fov_deg * 60.0 / self.size_px


def cutout_fov_deg(fov_width_arcmin: float, fov_height_arcmin: float) -> float:
    """Side of a square cutout that holds the frame at any rotation: its
    diagonal, plus `_FIELD_MARGIN`."""
    diagonal_arcmin = math.hypot(fov_width_arcmin, fov_height_arcmin)
    return diagonal_arcmin * _FIELD_MARGIN / 60.0


def fetch_cutout(
    ra_deg: float,
    dec_deg: float,
    fov_deg: float,
    *,
    size_px: int = DEFAULT_SIZE_PX,
    survey: str = DEFAULT_SURVEY,
) -> SurveyImage:
    """A cutout from hips2fits. Raises `SurveyImageUnavailable` on any
    network or HTTP failure, or if the response isn't a JPEG."""
    params = {
        "hips": survey,
        "width": str(size_px),
        "height": str(size_px),
        "fov": f"{fov_deg:.5f}",
        "projection": "TAN",
        "coordsys": "icrs",
        "ra": f"{ra_deg:.5f}",
        "dec": f"{dec_deg:.5f}",
        "format": "jpg",
    }
    url = f"{_API_URL}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT_S) as response:
            raw = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise SurveyImageUnavailable(f"hips2fits request failed: {exc}") from exc

    if not raw.startswith(_JPEG_MAGIC):
        raise SurveyImageUnavailable("hips2fits response is not a JPEG image")
    return SurveyImage(raw, ra_deg, dec_deg, fov_deg, size_px, survey)


def _cache_path(
    cache_dir: Path,
    ra_deg: float,
    dec_deg: float,
    fov_deg: float,
    size_px: int,
    survey: str,
) -> Path:
    # Rounded like the request itself, so equal requests share one file;
    # the survey ID is hashed since it contains slashes.
    survey_key = hashlib.sha1(survey.encode("utf-8")).hexdigest()[:10]
    name = f"{survey_key}_{ra_deg:.5f}_{dec_deg:+.5f}_{fov_deg:.5f}_{size_px}.jpg"
    return cache_dir / name


def fetch_cutout_cached(
    ra_deg: float,
    dec_deg: float,
    fov_deg: float,
    *,
    size_px: int = DEFAULT_SIZE_PX,
    survey: str = DEFAULT_SURVEY,
    cache_dir: Path | None = None,
) -> SurveyImage:
    """Same as `fetch_cutout`, but served from `cache_dir` (default:
    `DEFAULT_CACHE_DIR`, re-read here so tests can monkeypatch it) when
    the same cutout was fetched before. Never expires. A corrupt cache
    file counts as a miss; a failed cache write is ignored.
    """
    if cache_dir is None:
        cache_dir = DEFAULT_CACHE_DIR
    path = _cache_path(cache_dir, ra_deg, dec_deg, fov_deg, size_px, survey)

    try:
        cached = path.read_bytes()
    except OSError:
        cached = b""
    if cached.startswith(_JPEG_MAGIC):
        return SurveyImage(cached, ra_deg, dec_deg, fov_deg, size_px, survey)

    image = fetch_cutout(ra_deg, dec_deg, fov_deg, size_px=size_px, survey=survey)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write-then-rename, so an interrupted write never leaves a
        # truncated JPEG behind that later reads would accept.
        partial = path.with_suffix(".part")
        partial.write_bytes(image.jpeg_bytes)
        partial.replace(path)
    except OSError:
        pass  # best-effort — a missing cache just means a re-fetch
    return image
