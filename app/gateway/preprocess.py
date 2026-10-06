"""Preprocessing tried before OCR: even out light, flatten shadows, straighten skew.

Steps, in order:
1. Grey scale, then divide by an estimate of the page background. The background is
   the image with thin dark strokes removed (a morphological close) and then blurred,
   so dim photos come out white-backed and a shadow gradient disappears.
2. Deskew: try small rotations of a downscaled ink mask and keep the angle that makes
   text lines most distinct (largest variance of the row sums). Rotate only when that
   beats the unrotated page by 2 percent, so a straight page is left alone.

Images are uint8 arrays of shape (height, width, 3), BGR. The result has the same shape.
"""

import cv2
import numpy as np
import numpy.typing as npt

type Image = npt.NDArray[np.uint8]

_MAX_ANGLE_STEPS = 16  # +/- 8 degrees in half-degree steps
_STEP_DEGREES = 0.5
_MIN_GAIN = 1.02
_SMALL_SIDE = 400


def preprocess(image: Image) -> Image:
    """Flatten the lighting and straighten the page; same size and type as the input."""
    gray = np.asarray(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), dtype=np.uint8)
    straight = _deskew(_flatten_light(gray))
    return np.asarray(cv2.cvtColor(straight, cv2.COLOR_GRAY2BGR), dtype=np.uint8)


def _flatten_light(gray: Image) -> Image:
    height, width = gray.shape
    size = max(15, (min(height, width) // 15) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
    closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    background = cv2.GaussianBlur(closed, (0, 0), max(height, width) / 30)
    return np.asarray(cv2.divide(gray, background, scale=255), dtype=np.uint8)


def _deskew(gray: Image) -> Image:
    ink = _ink_mask(gray)
    base = _profile_variance(ink)
    best_angle = 0.0
    best_score = base
    for step in range(-_MAX_ANGLE_STEPS, _MAX_ANGLE_STEPS + 1):
        if step == 0:
            continue
        angle = step * _STEP_DEGREES
        score = _profile_variance(_rotate(ink, angle, fill=0))
        if score > best_score:
            best_angle, best_score = angle, score
    if best_score <= base * _MIN_GAIN:
        return gray
    return _rotate(gray, best_angle, fill=255)


def _ink_mask(gray: Image) -> Image:
    scale = min(1.0, _SMALL_SIDE / max(gray.shape))
    small = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    _, mask = cv2.threshold(small, 0, 1, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return np.asarray(mask, dtype=np.uint8)


def _profile_variance(ink: Image) -> float:
    return float(np.var(ink.sum(axis=1, dtype=np.float64)))


def _rotate(image: Image, degrees: float, fill: int) -> Image:
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), degrees, 1.0)
    rotated = cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=fill,
    )
    return np.asarray(rotated, dtype=np.uint8)
