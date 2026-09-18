import logging
from io import BytesIO

import cv2
import numpy as np
import requests
from PIL import Image


logger = logging.getLogger(__name__)


class ImageAgent:

    def __init__(self):
        self.timeout = 30

    # =========================================================
    # DOWNLOAD IMAGE
    # =========================================================

    def _download_image(self, url):

        try:

            response = requests.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like Gecko) "
                        "Chrome/120.0 Safari/537.36"
                    )
                },
                timeout=self.timeout,
            )

            response.raise_for_status()

            content_type = response.headers.get(
                "Content-Type",
                ""
            ).lower()

            if not content_type.startswith("image/"):

                logger.warning(
                    "Not an image: %s (%s)",
                    url,
                    content_type,
                )

                return None

            image = Image.open(
                BytesIO(response.content)
            )

            # Force loading
            image.load()

            return image

        except Exception as exc:

            logger.warning(
                "Could not download image: %s",
                exc,
            )

            return None

    # =========================================================
    # SCORE IMAGE
    # =========================================================

    def _score_image(self, image):

        width, height = image.size

        pixels = width * height

        # -----------------------------------------------------
        # Resolution score
        # -----------------------------------------------------

        if pixels >= 1920 * 1080:

            resolution_score = 10

        elif pixels >= 1280 * 720:

            resolution_score = 8

        elif pixels >= 900 * 600:

            resolution_score = 6

        elif pixels >= 700 * 500:

            resolution_score = 4

        else:

            resolution_score = 0

        # Very small images are rejected
        if resolution_score == 0:
            return 0

        # -----------------------------------------------------
        # Sharpness score
        # -----------------------------------------------------

        rgb = image.convert("RGB")

        array = np.array(rgb)

        gray = cv2.cvtColor(
            array,
            cv2.COLOR_RGB2GRAY,
        )

        sharpness = cv2.Laplacian(
            gray,
            cv2.CV_64F,
        ).var()

        if sharpness >= 500:

            sharpness_score = 10

        elif sharpness >= 250:

            sharpness_score = 8

        elif sharpness >= 120:

            sharpness_score = 6

        elif sharpness >= 80:

            sharpness_score = 4

        else:

            sharpness_score = 1

        # -----------------------------------------------------
        # Aspect ratio score
        # -----------------------------------------------------

        aspect_ratio = width / height

        if 1.25 <= aspect_ratio <= 1.75:

            aspect_score = 10

        elif 1.10 <= aspect_ratio <= 2.00:

            aspect_score = 7

        else:

            aspect_score = 4

        # -----------------------------------------------------
        # Overall image size score
        # -----------------------------------------------------

        size_score = min(
            10,
            pixels / (1920 * 1080) * 10,
        )

        # -----------------------------------------------------
        # Final score
        # -----------------------------------------------------

        final_score = (
            resolution_score * 0.40
            + sharpness_score * 0.40
            + aspect_score * 0.15
            + size_score * 0.05
        )

        return round(final_score, 2)

    # =========================================================
    # RANK ALL CANDIDATES
    # =========================================================

    def rank_candidates(
        self,
        food_name,
        candidates,
    ):

        ranked = []

        for index, candidate in enumerate(
            candidates,
            start=1,
        ):

            logger.info(
                "[%s] Checking candidate %d/%d",
                food_name,
                index,
                len(candidates),
            )

            image = self._download_image(
                candidate.image_url
            )

            if image is None:

                continue

            score = self._score_image(
                image
            )

            logger.info(
                "[%s] Candidate %d score: %.2f",
                food_name,
                index,
                score,
            )

            ranked.append({
                "candidate": candidate,
                "image": image,
                "score": score,
            })

        # Highest quality first

        ranked.sort(
            key=lambda x: x["score"],
            reverse=True,
        )

        return ranked

    # =========================================================
    # SELECT BEST
    # =========================================================

    def select_best(
        self,
        food_name,
        candidates,
    ):

        ranked = self.rank_candidates(
            food_name,
            candidates,
        )

        if not ranked:

            logger.warning(
                "[%s] No usable images found.",
                food_name,
            )

            return None

        logger.info(
            "[%s] Selected image with score %.2f",
            food_name,
            ranked[0]["score"],
        )

        return ranked[0]