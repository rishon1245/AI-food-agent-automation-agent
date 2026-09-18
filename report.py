import csv
from pathlib import Path


class ReportWriter:
    def __init__(self, filepath):
        self.filepath = Path(filepath)
        self.rows = []

    def add(
        self,
        food_item,
        image_found,
        image_processed,
        uploaded,
        drive_link=""
    ):
        self.rows.append({
            "food_item": food_item,
            "image_found": image_found,
            "image_processed": image_processed,
            "uploaded": uploaded,
            "drive_link": drive_link
        })

    def save(self):
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(
            self.filepath,
            "w",
            newline="",
            encoding="utf-8"
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "food_item",
                    "image_found",
                    "image_processed",
                    "uploaded",
                    "drive_link"
                ]
            )

            writer.writeheader()
            writer.writerows(self.rows)