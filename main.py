import logging
from pathlib import Path
import pandas as pd

from agent.excel_reader import ExcelFoodReader
from agent.image_search import ImageSearcher
from agent.image_agent import ImageAgent
from agent.image_processor import process_image
from agent.drive_uploader import DriveUploader
from agent.report import ReportWriter


# ============================================================
# CONFIGURATION
# ============================================================

EXCEL_FILE = Path("Assignment - Ai agent  - Sheet1.xlsx")

OUTPUT_DIR = Path("output/final_images")
TEMP_DIR = Path("output/temp")
REPORT_FILE = Path("reports/processing_report.csv")


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# DIRECTORY SETUP
# ============================================================

def prepare_directories():
    # Keep existing images so already-processed items can be skipped.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)


# ============================================================
# SAFE LOCAL FILENAME
# ============================================================

def safe_local_filename(name):
    """
    Makes a filename safe for Windows/local storage.

    Google Drive will still receive the EXACT food name.
    """

    invalid_chars = '<>:"/\\|?*'

    safe_name = name

    for char in invalid_chars:
        safe_name = safe_name.replace(char, "_")

    return safe_name.strip()


# ============================================================
# VALIDATE FINAL IMAGE
# ============================================================

def is_valid_output(file_path):

    if not file_path.exists():
        return False

    # Maximum 10 MB
    file_size = file_path.stat().st_size

    if file_size >= 10 * 1024 * 1024:
        logger.warning(
            "File is larger than 10 MB: %s",
            file_path
        )
        return False

    # Check image dimensions
    try:
        from PIL import Image

        with Image.open(file_path) as image:

            if image.size != (1800, 1200):
                logger.warning(
                    "Incorrect dimensions for %s: %s",
                    file_path,
                    image.size
                )
                return False

            if image.format not in ("JPEG", "PNG"):
                logger.warning(
                    "Invalid image format for %s: %s",
                    file_path,
                    image.format
                )
                return False

    except Exception as exc:

        logger.warning(
            "Could not validate image %s: %s",
            file_path,
            exc
        )

        return False

    return True


# ============================================================
# PREVIOUSLY PROCESSED ITEMS
# ============================================================

def load_previous_successes():
    """
    Read the previous processing report before it is overwritten.

    The final report only contains the public result columns. Any row with
    a non-empty Google Drive link is treated as already completed.
    """
    if not REPORT_FILE.exists():
        return {}

    try:
        df = pd.read_csv(REPORT_FILE)

        required_columns = {"food_item", "drive_link"}

        if not required_columns.issubset(df.columns):
            return {}

        previous_successes = {}

        for _, row in df.iterrows():
            if pd.isna(row["food_item"]):
                continue

            food_name = str(row["food_item"]).strip()

            if not food_name:
                continue

            if pd.isna(row["drive_link"]):
                continue

            drive_link = str(row["drive_link"]).strip()

            if not drive_link:
                continue

            previous_successes[food_name.casefold()] = {
                "source": "",
                "drive_link": drive_link
            }

        logger.info(
            "Previous report found: %d completed item(s) available for skip.",
            len(previous_successes)
        )

        return previous_successes

    except Exception as exc:
        logger.warning(
            "Could not read previous report for skip logic: %s",
            exc
        )
        return {}


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info("=" * 70)
    logger.info("AI FOOD IMAGE AUTOMATION AGENT")
    logger.info("=" * 70)

    # --------------------------------------------------------
    # Prepare folders
    # --------------------------------------------------------

    prepare_directories()

    # --------------------------------------------------------
    # Read Excel
    # --------------------------------------------------------

    logger.info("Reading Excel file: %s", EXCEL_FILE)

    reader = ExcelFoodReader(EXCEL_FILE)

    food_items = reader.read_food_items()

    # Read the old report BEFORE creating the new report.
    previous_successes = load_previous_successes()

    # --------------------------------------------------------
    # EXCEL MERGED-NAME GUARDRAIL
    # --------------------------------------------------------
    SUSPICIOUS_WORD_COUNT = 6

    flagged = [
        item.name
        for item in food_items
        if len(item.name.split()) > SUSPICIOUS_WORD_COUNT
    ]

    if flagged:
        logger.warning(
            "WARNING: %d item name(s) look unusually long and may "
            "contain two dishes merged without a line break.",
            len(flagged)
        )

        for name in flagged:
            logger.warning("   - %s", name)

        answer = input(
            "\nContinue processing these suspicious names? (y/n): "
        ).strip().lower()

        if answer != "y":
            raise RuntimeError(
                "Processing stopped. Review the Excel file and fix "
                "suspicious item names before running the pipeline."
            )

    logger.info(
        "Extracted %d food items from Excel.",
        len(food_items)
    )

    # --------------------------------------------------------
    # Initialize components
    # --------------------------------------------------------

    searcher = ImageSearcher()

    image_agent = ImageAgent()

    uploader = DriveUploader()

    report = ReportWriter(REPORT_FILE)

    successful = 0
    failed = 0

    # --------------------------------------------------------
    # Process EVERY food item
    # --------------------------------------------------------

    for index, food_item in enumerate(food_items, start=1):

        # IMPORTANT:
        # food_item is a FoodItem object.
        # We need its .name, not the entire object.

        food_name = food_item.name

        # --------------------------------------------------------
        # SKIP ALREADY-PROCESSED ITEMS
        # --------------------------------------------------------
        local_filename = safe_local_filename(food_name) + ".jpg"
        output_file = OUTPUT_DIR / local_filename
        name_key = food_name.strip().casefold()

        # If the item is already completed in the processing report,
        # always skip it. The Google Drive link is the source of truth.
        # This avoids unnecessary searching, downloading, processing,
        # and re-uploading even if the local copy is missing or invalid.
        if name_key in previous_successes:
            previous_data = previous_successes[name_key]

            logger.info(
                "[%d/%d] SKIPPING: %s — Already completed in processing report.",
                index,
                len(food_items),
                food_name
            )

            report.add(
                food_item=food_name,
                image_found=True,
                image_processed=True,
                uploaded=True,
                drive_link=previous_data["drive_link"]
            )

            successful += 1
            continue

        # If it wasn't in the old report, a valid local output is still
        # enough to avoid processing it again.
        if is_valid_output(output_file):
            logger.info(
                "[%d/%d] SKIPPING: %s — valid local output already exists.",
                index,
                len(food_items),
                food_name
            )

            report.add(
                food_item=food_name,
                image_found=True,
                image_processed=True,
                uploaded=True,
                drive_link=""
            )

            successful += 1
            continue

        logger.info("")
        logger.info("=" * 70)
        logger.info(
            "[%d/%d] Processing: %s",
            index,
            len(food_items),
            food_name
        )
        logger.info("=" * 70)

        output_file = None
        temp_file = None

        try:

            # ------------------------------------------------
            # STEP 1: Search for images
            # ------------------------------------------------

            logger.info(
                "[%s] Searching for images...",
                food_name
            )

            candidates = searcher.search(food_name)

            if not candidates:

                logger.warning(
                    "[%s] No image candidates found.",
                    food_name
                )

                report.add(
                    food_item=food_name,
                    image_found=False,
                    image_processed=False,
                    uploaded=False,
                    drive_link=""
                )

                failed += 1
                continue

            logger.info(
                "[%s] Found %d candidates.",
                food_name,
                len(candidates)
            )

            # ------------------------------------------------
            # STEP 2: Rank candidates
            # ------------------------------------------------

            ranked_candidates = image_agent.rank_candidates(
                food_name,
                candidates
            )

            if not ranked_candidates:

                logger.warning(
                    "[%s] No usable images after quality check.",
                    food_name
                )

                report.add(
                    food_item=food_name,
                    image_found=True,
                    image_processed=False,
                    uploaded=False,
                    drive_link=""
                )

                failed += 1
                continue

            # ------------------------------------------------
            # STEP 3: Try candidates one by one
            # ------------------------------------------------

            processed_successfully = False

            for candidate_number, ranked in enumerate(
                ranked_candidates,
                start=1
            ):

                candidate = ranked["candidate"]
                image = ranked["image"]
                score = ranked["score"]

                logger.info(
                    "[%s] Trying candidate %d/%d | Score: %.2f",
                    food_name,
                    candidate_number,
                    len(ranked_candidates),
                    score
                )

                try:

                    # ----------------------------------------
                    # Create temporary file
                    # ----------------------------------------

                    temp_file = (
                        TEMP_DIR /
                        f"{safe_local_filename(food_name)}_temp.jpg"
                    )

                    # Save downloaded PIL image
                    image.convert("RGB").save(
                        temp_file,
                        "JPEG",
                        quality=95
                    )

                    # ----------------------------------------
                    # Create final filename
                    # ----------------------------------------

                    local_filename = (
                        safe_local_filename(food_name)
                        + ".jpg"
                    )

                    output_file = OUTPUT_DIR / local_filename

                    # ----------------------------------------
                    # Process image
                    # 1800 x 1200
                    # < 10 MB
                    # quality validation
                    # ----------------------------------------

                    logger.info(
                        "[%s] Processing image...",
                        food_name
                    )

                    process_image(
                        temp_file,
                        output_file
                    )

                    # ----------------------------------------
                    # Validate output
                    # ----------------------------------------

                    if not is_valid_output(output_file):

                        raise RuntimeError(
                            "Final image failed validation."
                        )

                    logger.info(
                        "[%s] Image processed successfully.",
                        food_name
                    )

                    # ----------------------------------------
                    # IMPORTANT:
                    # Drive receives EXACT food name
                    # ----------------------------------------

                    drive_filename = f"{food_name}.jpg"

                    logger.info(
                        "[%s] Uploading to Google Drive as: %s",
                        food_name,
                        drive_filename
                    )

                    drive_link = uploader.upload(
                        output_file,
                        drive_filename
                    )

                    # ----------------------------------------
                    # SUCCESS
                    # ----------------------------------------

                    logger.info(
                        "[%s] Successfully uploaded.",
                        food_name
                    )

                    report.add(
                        food_item=food_name,
                        image_found=True,
                        image_processed=True,
                        uploaded=True,
                        drive_link=drive_link
                    )

                    successful += 1
                    processed_successfully = True

                    # Clean temp file
                    if temp_file and temp_file.exists():
                        temp_file.unlink()

                    break

                except Exception as exc:

                    logger.warning(
                        "[%s] Candidate %d failed: %s",
                        food_name,
                        candidate_number,
                        exc
                    )

                    # Delete failed output
                    if output_file and output_file.exists():
                        output_file.unlink()

                    # Delete temp file
                    if temp_file and temp_file.exists():
                        temp_file.unlink()

                    continue

            # ------------------------------------------------
            # STEP 4: All candidates failed
            # ------------------------------------------------

            if not processed_successfully:

                logger.error(
                    "[%s] All image candidates failed.",
                    food_name
                )

                report.add(
                    food_item=food_name,
                    image_found=True,
                    image_processed=False,
                    uploaded=False,
                    drive_link=""
                )

                failed += 1

        except Exception as exc:

            logger.exception(
                "[%s] Unexpected error: %s",
                food_name,
                exc
            )

            report.add(
                food_item=food_name,
                image_found=False,
                image_processed=False,
                uploaded=False,
                drive_link=""
            )

            failed += 1

    # --------------------------------------------------------
    # SAVE REPORT
    # --------------------------------------------------------

    report.save()

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    logger.info("")
    logger.info("=" * 70)
    logger.info("PROCESSING COMPLETE")
    logger.info("=" * 70)

    logger.info(
        "Total food items : %d",
        len(food_items)
    )

    logger.info(
        "Successful       : %d",
        successful
    )

    logger.info(
        "Failed           : %d",
        failed
    )

    logger.info(
        "Report           : %s",
        REPORT_FILE
    )

    logger.info("=" * 70)


if __name__ == "__main__":
    main()