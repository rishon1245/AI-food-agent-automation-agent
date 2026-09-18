import re
from dataclasses import dataclass
from pathlib import Path

import openpyxl


@dataclass
class FoodItem:
    name: str
    source_row: int


class ExcelFoodReader:

    def __init__(self, excel_file):
        self.excel_file = Path(excel_file)

    def read_food_items(self):

        if not self.excel_file.exists():
            raise FileNotFoundError(
                f"Excel file not found: {self.excel_file}"
            )

        workbook = openpyxl.load_workbook(
            self.excel_file,
            data_only=True
        )

        # Use the first sheet
        sheet = workbook[workbook.sheetnames[0]]

        food_items = []

        # Find the "item_name" column
        headers = {}

        for cell in sheet[2]:
            if cell.value:
                headers[str(cell.value).strip().lower()] = cell.column

        if "item_name" not in headers:
            raise ValueError(
                "Could not find 'item_name' column in Excel."
            )

        item_column = headers["item_name"]

        # Read food names
        for row_number in range(3, sheet.max_row + 1):

            value = sheet.cell(
                row=row_number,
                column=item_column
            ).value

            if value is None:
                continue

            text = str(value).strip()

            if not text:
                continue

            # Split explicit line-separated items
            parts = re.split(r"[\r\n]+", text)

            for part in parts:

                part = part.strip()

                if not part:
                    continue

                food_items.append(
                    FoodItem(
                        name=part,
                        source_row=row_number
                    )
                )

        # Remove exact duplicates while preserving order
        unique_items = []
        seen = set()

        for item in food_items:

            key = item.name.strip().lower()

            if key not in seen:

                seen.add(key)
                unique_items.append(item)

        print(
            f"Extracted {len(unique_items)} food items from Excel."
        )

        return unique_items