from pathlib import Path
from PIL import Image, ImageOps
import cv2

def _blur_score(path):
    img = cv2.imread(str(path))
    if img is None:
        return 0.0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())

def process_image(input_path, output_path, target_size=(1800, 1200), max_mb=10):
    """
    Produces exactly 1800x1200 JPG while preserving the whole image as much
    as possible. ImageOps.fit performs a controlled crop to the target aspect
    ratio, then resizing gives the exact required dimensions.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")

        # Fit to 3:2 with a small controlled crop. This avoids distortion.
        img = ImageOps.fit(
            img,
            target_size,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )

        # Save with high quality first.
        quality = 92
        while quality >= 55:
            img.save(
                output_path,
                "JPEG",
                quality=quality,
                optimize=True,
                progressive=True,
            )

            size_mb = output_path.stat().st_size / (1024 * 1024)
            if size_mb < max_mb:
                break
            quality -= 5

    # Hard checks required by the assignment.
    with Image.open(output_path) as final:
        if final.size != target_size:
            raise RuntimeError(
                f"Final dimensions are {final.size}, expected {target_size}."
            )

    size_mb = output_path.stat().st_size / (1024 * 1024)
    if size_mb >= max_mb:
        raise RuntimeError(f"Could not compress below {max_mb} MB.")

    if _blur_score(output_path) < 35:
        raise RuntimeError("Processed image failed final sharpness check.")

    return output_path
