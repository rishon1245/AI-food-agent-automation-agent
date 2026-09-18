import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

from .models import ImageCandidate


logger = logging.getLogger(__name__)


class ImageSearcher:
    ENDPOINT = "https://google.serper.dev/images"

    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")

        if not self.api_key:
            raise RuntimeError(
                "SERPER_API_KEY is missing. Add it to .env."
            )

    def search(self, food_name: str, limit: int = 5):
        """
        Search for food images.

        The search query includes the food name and Indian food context
        to improve relevance.
        """

        queries = [
            f"{food_name} Indian restaurant food dish",
            f"{food_name} Indian food",
        ]

        for query in queries:

            try:
                response = requests.post(
                    self.ENDPOINT,
                    headers={
                        "X-API-KEY": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "q": query,
                        "num": limit,
                    },
                    timeout=30,
                )

                response.raise_for_status()

                data = response.json()
                results = data.get("images", [])

                candidates = []

                for result in results:

                    image_url = result.get("imageUrl")

                    source_url = (
                        result.get("link")
                        or result.get("source")
                        or ""
                    )

                    title = (
                        result.get("title")
                        or food_name
                    )

                    if image_url:

                        candidates.append(
                            ImageCandidate(
                                image_url=image_url,
                                source_url=source_url,
                                title=title,
                            )
                        )

                if candidates:
                    logger.info(
                        "[%s] Found %d image candidates.",
                        food_name,
                        len(candidates),
                    )

                    return candidates

            except Exception as exc:

                logger.warning(
                    "[%s] Search failed: %s",
                    food_name,
                    exc,
                )

        logger.warning(
            "[%s] No image candidates found.",
            food_name,
        )

        return []