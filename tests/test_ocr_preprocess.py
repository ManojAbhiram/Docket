"""OCR preprocessing: brighten dim photos, flatten shadows, straighten skew."""

import cv2
import numpy as np
import numpy.typing as npt
import pytest

from app.gateway.preprocess import preprocess

type Image = npt.NDArray[np.uint8]


def _white_canvas_with_bars() -> Image:
    canvas = np.full((200, 300, 3), 255, dtype=np.uint8)
    canvas[30:36, 20:280] = 0
    canvas[90:96, 20:280] = 0
    canvas[150:156, 20:280] = 0
    return canvas


def _scaled(image: Image, factor: float) -> Image:
    return (image * factor).astype(np.uint8)


def _with_vertical_ramp(image: Image, bottom: float) -> Image:
    ramp = np.linspace(1.0, bottom, image.shape[0])
    return (image * ramp[:, None, None]).astype(np.uint8)


def _rotated(image: Image, degrees: float) -> Image:
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), degrees, 1.0)
    rotated = cv2.warpAffine(
        image, matrix, (width, height), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255)
    )
    return np.asarray(rotated, dtype=np.uint8)


def _row_profile_variance(image: Image) -> float:
    return float(image.astype(np.float64).sum(axis=(1, 2)).var())


@pytest.fixture(scope="module")
def page() -> Image:
    return _white_canvas_with_bars()


@pytest.fixture(scope="module")
def striped_page() -> Image:
    """Several long black bars across the full width, so skew smears the row profile."""
    canvas = np.full((200, 300, 3), 255, dtype=np.uint8)
    for top in (30, 60, 90, 120, 150):
        canvas[top : top + 6, 10:290] = 0
    return canvas


def test_output_keeps_the_input_shape_and_dtype(page: Image) -> None:
    result = preprocess(page)

    assert result.shape == page.shape
    assert result.dtype == np.uint8


def test_a_clean_page_stays_mostly_white(page: Image) -> None:
    result = preprocess(page)

    assert result.mean() > 200


def test_a_dark_photo_comes_out_brighter_than_it_went_in(page: Image) -> None:
    dark = _scaled(page, 0.5)

    result = preprocess(dark)

    assert result.mean() > dark.mean()
    assert result[:20, :20].mean() >= 200


def test_a_shadow_gradient_is_evened_out(page: Image) -> None:
    shaded = _with_vertical_ramp(page, bottom=0.5)
    third = shaded.shape[0] // 3

    result = preprocess(shaded)

    assert abs(float(shaded[:third].mean()) - float(shaded[-third:].mean())) > 20
    assert abs(float(result[:third].mean()) - float(result[-third:].mean())) <= 20


def test_a_skewed_page_is_straightened(striped_page: Image) -> None:
    skewed = _rotated(striped_page, 3.0)

    result = preprocess(skewed)

    assert _row_profile_variance(result) > _row_profile_variance(skewed)


def test_the_same_input_gives_the_same_output(page: Image) -> None:
    first = preprocess(page)
    second = preprocess(page)

    assert np.array_equal(first, second)
