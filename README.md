# AI Food Image Automation Agent

## 1. Project Overview
The AI Food Image Automation Agent is a Python-based automation system that processes food menu items from an Excel file and automatically obtains suitable food images for each item.
The system automates the complete workflow from reading food names to image processing, Google Drive upload, and report generation.

## 2. Objectives
- Read food items automatically from an Excel spreadsheet.
- Search for suitable images for each food item.
- Evaluate available images based on technical image quality (resolution, sharpness, aspect ratio).
- Process images according to the required specifications.
- Rename images using the exact food item name.
- Upload processed images to Google Drive.
- Generate a CSV report containing the processing results.
- Support batch processing and resumable execution.

## 3. Workflow
 
Excel File
    ↓
Extract Food Items
    ↓
Search Food Images
    ↓
Select Suitable Image
    ↓
Image Quality Evaluation
    ↓
Resize & Process Image
    ↓
Rename Using Food Name
    ↓
Upload to Google Drive
    ↓
Generate Processing Report
 

## 4. Image Requirements
The processed images are designed to meet the assignment requirements:
- Format: JPG/PNG
- Resolution: 1800 × 1200 pixels
- Maximum file size: 10 MB
- Good visual quality
- Food should be clearly visible
- Suitable for menu/catalogue use

## 5. Project Structure
 
AI_Food_Image_Agent_Project/
│
├── main.py
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── Assignment - Ai agent  - Sheet1.xlsx
│
├── agent/
│   ├── __init__.py
│   ├── excel_reader.py
│   ├── image_search.py
│   ├── image_agent.py
│   ├── image_processor.py
│   ├── drive_uploader.py
│   ├── models.py
│   └── report.py
│
└── reports/
    └── processing_report.csv
 

## 6. Technologies Used
- Python
- Pandas / OpenPyXL — Excel data processing
- Pillow / OpenCV — image resizing and quality analysis
- Google Drive API — image upload
- CSV — processing report
- Google OAuth — Drive authentication
- Serper.dev — image search

## 7. Setup

**Step 1 — Create a virtual environment**
 
python -m venv .venv
 
Activate it (Windows):
 
.venv\Scripts\activate
 

**Step 2 — Install dependencies**
 
pip install -r requirements.txt
 

**Step 3 — Configure environment variables**

Copy `.env.example` to `.env` and fill in:
- `SERPER_API_KEY` — get a free key at [serper.dev](https://serper.dev)
- `GOOGLE_DRIVE_FOLDER_ID` — the target Drive folder's ID
- `GOOGLE_OAUTH_CLIENT_FILE` / `GOOGLE_OAUTH_TOKEN_FILE` — see Step 4

**Step 4 — Google Drive OAuth credentials**

1. In Google Cloud Console, enable the Drive API and create an **OAuth client ID** (type: Desktop app).
2. Download the client secret JSON and save it at `credentials/client_secret.json` (or wherever `GOOGLE_OAUTH_CLIENT_FILE` points).
3. On first run, a browser window opens to authorize access once. After that, `token.json` is cached and reused — no further manual login is needed.

Never commit `.env`, `credentials/`, or `token.json` to version control (already covered in `.gitignore`).

## 8. Input
The system reads: `Assignment - Ai agent  - Sheet1.xlsx`
Food names are extracted from the `item_name` column.

If two dish names are merged into a single cell without a line-break separator, the pipeline detects and flags this before processing (see Section 11).

## 9. Running the Project
From the project directory:
 
python main.py
 
The agent reads the Excel file and processes the food items automatically. If items from a previous run already succeeded (per `reports/processing_report.csv` and/or a valid local output file), they are skipped rather than reprocessed — so re-running after a small fix only touches what actually changed.

## 10. Output
The final processing report is stored at:
 
reports/processing_report.csv
 
Columns: `food_item`, `image_found`, `image_processed`, `uploaded`, `drive_link`

Processed images are uploaded to the configured Google Drive folder, named exactly after the food item (e.g. `Paneer Butter Masala.jpg`).

## 11. Error Handling & Safeguards
The system processes food items individually so that an issue with one item never stops the batch. It also supports:
- Automatic fallback to the next-ranked image candidate if one fails quality/processing checks
- Post-processing validation (exact dimensions, size limit, format)
- Resumable execution — previously completed items are detected and skipped
- A merged-name guardrail: item names that look unusually long (possibly two dishes merged into one Excel cell without a separator) are flagged, with a manual confirm prompt before continuing

## 12. Testing Result
A full run against the complete cleaned dataset (254 unique food items, derived from 390 source rows after de-duplication and fixing 15 rows with merged dish names) completed with:

- **Total food items:** 254
- **Completed successfully:** 254 (0 failed)
- **Status breakdown:** items are marked `SUCCESS` the first time they're processed, and `SKIPPED` on later runs once already confirmed successful — this run's report reflects that all 254 items have a confirmed, valid processed image uploaded to Drive.

The CSV report contains the processing result and Google Drive link for every item.

## 13. Conclusion
The project automates the repetitive process of collecting, processing, and organizing food images from an Excel-based menu, combining automated image search, quality evaluation, image processing, Google Drive upload, and CSV reporting into a single unattended workflow.
