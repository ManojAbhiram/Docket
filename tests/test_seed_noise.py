"""Photo noise applied to a rendered document: each effect shows up and is repeatable."""

import cv2
import numpy as np
import numpy.typing as npt
import pytest

from seed.dataset import NoiseSpec
from seed.render import add_photo_noise

type Image = npt.NDArray[np.uint8]

BORDER_COLOUR = (232, 232, 232)


def _neutral(
    blur_radius: float = 0.0,
    skew_degrees: float = 0.0,
    shadow_strength: float = 0.0,
    low_light: float = 1.0,
) -> NoiseSpec:
    return NoiseSpec(
        blur_radius=blur_radius,
        skew_degrees=skew_degrees,
        shadow_strength=shadow_strength,
        low_light=low_light,
    )


@pytest.fixture(scope="module")
def page() -> Image:
    """White 200x300 canvas with three black bars, one in each third of the rows."""
    canvas = np.full((200, 300, 3), 255, dtype=np.uint8)
    canvas[10:15, 20:280] = 0
    canvas[90:95, 20:280] = 0
    canvas[150:155, 20:280] = 0
    return canvas


def _laplacian_variance(image: Image) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def test_a_neutral_spec_returns_the_input_unchanged(page: Image) -> None:
    result = add_photo_noise(page, _neutral())

    assert np.array_equal(result, page)


def test_output_keeps_the_input_shape_and_dtype(page: Image) -> None:
    result = add_photo_noise(page, _neutral(blur_radius=1.5, skew_degrees=3.0))

    assert result.shape == page.shape
    assert result.dtype == np.uint8


def test_blur_lowers_the_laplacian_variance(page: Image) -> None:
    result = add_photo_noise(page, _neutral(blur_radius=1.5))

    assert _laplacian_variance(result) < _laplacian_variance(page)


def test_shadow_darkens_the_bottom_third_more_than_the_top_third(page: Image) -> None:
    result = add_photo_noise(page, _neutral(shadow_strength=0.4))

    third = page.shape[0] // 3
    assert page[:third].mean() == page[-third:].mean()
    assert result[-third:].mean() < result[:third].mean()


def test_low_light_darkens_the_whole_image(page: Image) -> None:
    result = add_photo_noise(page, _neutral(low_light=0.5))

    assert result.mean() < 0.6 * page.mean()


def test_skew_changes_the_image_and_keeps_its_size(page: Image) -> None:
    result = add_photo_noise(page, _neutral(skew_degrees=3.0))

    assert result.shape == (200, 300, 3)
    assert not np.array_equal(result, page)


def test_skew_fills_the_exposed_corners_with_the_border_colour(page: Image) -> None:
    result = add_photo_noise(page, _neutral(skew_degrees=3.0))

    corners = [tuple(int(v) for v in result[y, x]) for y in (0, -1) for x in (0, -1)]
    assert BORDER_COLOUR in corners


def test_the_same_call_twice_returns_equal_arrays(page: Image) -> None:
    noise = NoiseSpec(blur_radius=1.2, skew_degrees=-2.5, shadow_strength=0.3, low_light=0.6)

    first = add_photo_noise(page, noise)
    second = add_photo_noise(page, noise)

    assert np.array_equal(first, second)
