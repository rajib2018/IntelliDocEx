# Basic Invoice OCR → Excel Streamlit App

A minimal intelligent document processing app that extracts invoice information from PDF or image uploads and produces a downloadable Excel file.

Features
- Upload invoice PDF or image (jpg/png/pdf).
- OCR via Tesseract (pdfs converted to images using pdf2image).
- Extracts key fields: vendor (heuristic), invoice number, date, total amount.
- Attempts to parse simple line items (very basic heuristic).
- Download results as an Excel file (Summary + LineItems).

Requirements
- Python 3.8+
- System packages:
  - Tesseract OCR (install tesseract on your OS). On macOS: `brew install tesseract`. On Ubuntu/Debian: `sudo apt install tesseract-ocr`.
  - Poppler for pdf2image. On macOS: `brew install poppler`. On Ubuntu: `sudo apt install poppler-utils`.

Install Python dependencies
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run locally
```bash
streamlit run app.py
```

Deploying
- Streamlit Cloud: push this repo to GitHub and create a new app from the repo. Make sure runtime has Tesseract and Poppler or provide a Dockerfile (included).
- Docker: build the included Dockerfile if you want an image that includes system deps.

Notes and limitations
- This is intentionally simple. It uses OCR text and regex heuristics; it will not match advanced or heavily-formatted invoices.
- For production-grade IDP, consider adding layout-aware OCR, trained parsers, table extractors (Camelot/Tabula, deep learning table detection), or commercial APIs.

Files
- app.py — Streamlit app (UI + orchestration)
- ocr_utils.py — OCR and extraction helpers
- requirements.txt — Python packages
- Dockerfile — optional Docker image with Tesseract + Poppler
- .gitignore, LICENSE

Have a PDF or image? Upload it in the UI and click "Process" — you'll get a preview and a button to download the results as an Excel workbook.
