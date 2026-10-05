"""Render the synthetic HTML to noisy phone-style PNGs.

Needs two packages that are not in pyproject.toml yet: playwright (with its
chromium build) and pillow. Only `seed.__main__ --png` imports this module, so
the data layer and its tests run without them.
"""

from pathlib import Path

from PIL import Image, ImageChops, ImageFilter
from playwright.sync_api import sync_playwright

from seed.dataset import Dataset, NoiseSpec
from seed.pages import render_html

_VIEWPORT = {"width": 800, "height": 1000}
_BACKGROUND = (232, 232, 232)


def render_all(dataset: Dataset, out_dir: Path) -> list[Path]:
    """Write one PNG per document into `out_dir` and return their paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    apps = {app.application_id: app for app in dataset.applications}
    written: list[Path] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=_VIEWPORT)
        for doc in dataset.documents:
            page.set_content(render_html(doc, apps[doc.application_id]))
            clean_path = out_dir / f"_clean_{doc.file_name}"
            page.screenshot(path=str(clean_path), full_page=True)
            with Image.open(clean_path) as clean:
                noisy = add_photo_noise(clean.convert("RGB"), doc.noise)
            target = out_dir / doc.file_name
            noisy.save(target)
            clean_path.unlink()
            written.append(target)
        browser.close()
    return written


def add_photo_noise(image: Image.Image, noise: NoiseSpec) -> Image.Image:
    """Blur, a shadow gradient, then a small skew, as a phone photo would show."""
    blurred = image.filter(ImageFilter.GaussianBlur(noise.blur_radius))
    gradient = Image.linear_gradient("L").resize(blurred.size)
    strength = noise.shadow_strength
    shade = gradient.point(lambda value: 255 - int(strength * value)).convert("RGB")
    shadowed = ImageChops.multiply(blurred, shade)
    return shadowed.rotate(
        noise.skew_degrees,
        expand=True,
        resample=Image.Resampling.BICUBIC,
        fillcolor=_BACKGROUND,
    )
