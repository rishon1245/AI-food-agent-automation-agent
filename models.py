from dataclasses import dataclass
from pathlib import Path

@dataclass
class FoodItem:
    name: str
    source_row: int

@dataclass
class ImageCandidate:
    image_url: str
    source_url: str
    title: str
    local_path: Path | None = None
