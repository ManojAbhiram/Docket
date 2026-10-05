"""Turn clean page screenshots into noisy phone-style photos with OpenCV.

Three stages, run in this order from the repository root:

    uv run python -m seed                  # HTML pages, CSV, labels, render script
    bash data/seed/render-clean.sh         # playwright-cli screenshots each page
    uv run python -m seed --noise          # this module: blur, shadow, low light, skew

Images are uint8 arrays of shape (height, width, 3) in BGR order, as OpenCV reads them.
The noise is deterministic: every document carries its own settings (see `NoiseSpec`).
"""

from pathlib import Path

import cv2
import numpy as np
import numpy.typing as npt

from seed.dataset import Dataset, NoiseSpec

type Image = npt.NDArray[np.uint8]

_BORDER = (232, 232, 232)


def add_photo_noise(image: Image, noise: NoiseSpec) -> Image:
    """Blur, a shadow falling toward the bottom, low light, then a small skew."""
    out = image
    if noise.blur_radius > 0:
        out = np.asarray(cv2.GaussianBlur(out, (0, 0), noise.blur_radius), dtype=np.uint8)
    if noise.shadow_strength > 0:
        ramp = np.linspace(1.0, 1.0 - noise.shadow_strength, out.shape[0], dtype=np.float32)
        shaded = out.astype(np.float32) * ramp[:, None, None]
        out = np.clip(shaded, 0, 255).astype(np.uint8)
    if noise.low_light < 1.0:
        out = np.asarray(cv2.convertScaleAbs(out, alpha=noise.low_light), dtype=np.uint8)
    if noise.skew_degrees != 0:
        height, width = out.shape[:2]
        matrix = cv2.getRotationMatrix2D((width / 2, height / 2), noise.skew_degrees, 1.0)
        out = np.asarray(
            cv2.warpAffine(
                out,
                matrix,
                (width, height),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=_BORDER,
            ),
            dtype=np.uint8,
        )
    return out


def render_noisy(dataset: Dataset, clean_dir: Path, out_dir: Path) -> list[Path]:
    """Read each clean screenshot, add its noise and write the PNG into `out_dir`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for doc in dataset.documents:
        source = clean_dir / doc.file_name
        image = cv2.imread(str(source), cv2.IMREAD_COLOR)
        if image is None:
            msg = f"clean screenshot missing or unreadable: {source} (run render-clean.sh first)"
            raise FileNotFoundError(msg)
        noisy = add_photo_noise(np.asarray(image, dtype=np.uint8), doc.noise)
        target = out_dir / doc.file_name
        if not cv2.imwrite(str(target), noisy):
            msg = f"could not write {target}"
            raise OSError(msg)
        written.append(target)
    return written
