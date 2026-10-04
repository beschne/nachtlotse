"""hips2fits client tests — network is always mocked here; the test suite
must stay offline-safe (see CLAUDE.md's guiding principle)."""

from __future__ import annotations

import math
import urllib.error
import urllib.parse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nachtlotse import sky_survey

_FAKE_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def _mock_response(raw: bytes) -> MagicMock:
    response = MagicMock()
    response.read.return_value = raw
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def _query(mock_urlopen: MagicMock) -> dict[str, str]:
    url = mock_urlopen.call_args.args[0]
    return {
        key: values[0]
        for key, values in urllib.parse.parse_qs(
            urllib.parse.urlparse(url).query
        ).items()
    }


def test_cutout_fov_holds_the_frame_at_any_rotation() -> None:
    fov_deg = sky_survey.cutout_fov_deg(240.0, 135.0)
    assert fov_deg * 60.0 > math.hypot(240.0, 135.0)
    assert fov_deg * 60.0 < math.hypot(240.0, 135.0) * 1.5


def test_fetch_cutout_requests_a_north_up_tan_icrs_jpeg() -> None:
    with patch(
        "urllib.request.urlopen", return_value=_mock_response(_FAKE_JPEG)
    ) as mock_urlopen:
        image = sky_survey.fetch_cutout(10.6847, 41.2692, 5.3, size_px=512)

    query = _query(mock_urlopen)
    assert query["hips"] == sky_survey.DEFAULT_SURVEY
    assert query["projection"] == "TAN"
    assert query["coordsys"] == "icrs"
    assert query["format"] == "jpg"
    assert (query["width"], query["height"]) == ("512", "512")
    assert float(query["ra"]) == pytest.approx(10.6847)
    assert float(query["dec"]) == pytest.approx(41.2692)
    assert float(query["fov"]) == pytest.approx(5.3)
    # No rotation requested: hips2fits' default is north up, east left —
    # the convention engine.framing_preview's offsets assume.
    assert "rotation_angle" not in query

    assert image.jpeg_bytes == _FAKE_JPEG
    assert image.arcmin_per_px == pytest.approx(5.3 * 60.0 / 512)
    assert "DSS2" in image.credit


def test_fetch_cutout_raises_on_network_error() -> None:
    with (
        patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline")),
        pytest.raises(sky_survey.SurveyImageUnavailable),
    ):
        sky_survey.fetch_cutout(10.0, 40.0, 3.0)


def test_fetch_cutout_raises_on_a_non_image_response() -> None:
    with (
        patch(
            "urllib.request.urlopen",
            return_value=_mock_response(b'{"title": "Unknown HiPS"}'),
        ),
        pytest.raises(sky_survey.SurveyImageUnavailable),
    ):
        sky_survey.fetch_cutout(10.0, 40.0, 3.0)


def test_fetch_cutout_cached_fetches_once_then_serves_from_disk(
    tmp_path: Path,
) -> None:
    with patch(
        "urllib.request.urlopen", return_value=_mock_response(_FAKE_JPEG)
    ) as mock_urlopen:
        first = sky_survey.fetch_cutout_cached(10.0, 40.0, 3.0, cache_dir=tmp_path)
        second = sky_survey.fetch_cutout_cached(10.0, 40.0, 3.0, cache_dir=tmp_path)

    assert mock_urlopen.call_count == 1
    assert first.jpeg_bytes == second.jpeg_bytes == _FAKE_JPEG
    assert [p.suffix for p in tmp_path.iterdir()] == [".jpg"]


def test_fetch_cutout_cached_works_offline_once_cached(tmp_path: Path) -> None:
    with patch("urllib.request.urlopen", return_value=_mock_response(_FAKE_JPEG)):
        sky_survey.fetch_cutout_cached(10.0, 40.0, 3.0, cache_dir=tmp_path)
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
        image = sky_survey.fetch_cutout_cached(10.0, 40.0, 3.0, cache_dir=tmp_path)
    assert image.jpeg_bytes == _FAKE_JPEG


def test_fetch_cutout_cached_keys_by_position_and_field(tmp_path: Path) -> None:
    with patch(
        "urllib.request.urlopen", return_value=_mock_response(_FAKE_JPEG)
    ) as mock_urlopen:
        sky_survey.fetch_cutout_cached(10.0, 40.0, 3.0, cache_dir=tmp_path)
        sky_survey.fetch_cutout_cached(10.0, 41.0, 3.0, cache_dir=tmp_path)
        sky_survey.fetch_cutout_cached(10.0, 40.0, 4.0, cache_dir=tmp_path)
    assert mock_urlopen.call_count == 3


def test_fetch_cutout_cached_treats_a_corrupt_file_as_a_miss(tmp_path: Path) -> None:
    with patch("urllib.request.urlopen", return_value=_mock_response(_FAKE_JPEG)):
        sky_survey.fetch_cutout_cached(10.0, 40.0, 3.0, cache_dir=tmp_path)
    (cached_file,) = tmp_path.iterdir()
    cached_file.write_bytes(b"garbage")

    with patch(
        "urllib.request.urlopen", return_value=_mock_response(_FAKE_JPEG)
    ) as mock_urlopen:
        image = sky_survey.fetch_cutout_cached(10.0, 40.0, 3.0, cache_dir=tmp_path)
    assert mock_urlopen.call_count == 1
    assert image.jpeg_bytes == _FAKE_JPEG
    assert cached_file.read_bytes() == _FAKE_JPEG


def test_fetch_cutout_cached_propagates_unavailable_on_a_miss(tmp_path: Path) -> None:
    with (
        patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline")),
        pytest.raises(sky_survey.SurveyImageUnavailable),
    ):
        sky_survey.fetch_cutout_cached(10.0, 40.0, 3.0, cache_dir=tmp_path)
    assert not any(tmp_path.iterdir())
