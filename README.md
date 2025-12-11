# Streamlit Invoice OCR → Excel (Streamlit Community Cloud ready)

A minimal Intelligent Document Processing (IDP) app that extracts key invoice fields from PDF or image uploads and exports the results to a downloadable Excel file. This repo is prepared to run on Streamlit Community Cloud (free tier) by using Google Cloud Vision for OCR and PyMuPDF to render PDFs to images (no system `apt` packages required).

Highlights
- Upload invoice PDF or image (jpg/png/pdf).
- OCR via Google Cloud Vision API (fast and accurate).
- PDFs rendered with PyMuPDF (pure-Python, no Poppler).
- Extracts key fields: vendor (heuristic), invoice number, date, total amount.
- Attempts to parse simple line items (naive heuristic).
- Download results as an Excel file (Summary + LineItems).
- Streamlit Community Cloud compatible (no apt-get required).

Important: You MUST provide Google Cloud Vision credentials in Streamlit secrets to enable OCR.

Quick setup (local)
1. Create virtual env and install:
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

2. Run locally:
   streamlit run app.py

Deploy to Streamlit Community Cloud (free)
1. Push this repo to GitHub.
2. On Streamlit Cloud, create a new app from your repo.
3. Add your Google Cloud service account JSON to the app's **Secrets**:
   - Open "Settings" → "Secrets" for your Streamlit app.
   - Add a secret with key: `GCP_CREDENTIALS_JSON`
   - For the value paste the entire service account JSON (the JSON object as plain text).
   - Example:
     {
       "type": "service_account",
       "project_id": "...",
       ...
     }
4. Start the app. The app will use the Vision API via the credentials stored in secrets.

Notes on costs and quotas
- Google Cloud Vision API may incur charges after free-tier usage. Monitor your billing and quotas in Google Cloud Console.
- For small testing or occasional use, the cost is usually very small.

If you prefer not to use Google Cloud Vision, I can:
- add support for another cloud OCR (Azure, AWS, or OCR.space),
- or provide a Docker-based deployment guide that runs Tesseract/Poppler (for Render/Cloud Run).

Files included
- app.py — Streamlit app with jazzed UI
- ocr_utils.py — OCR helpers (Vision + PDF rendering) and extraction heuristics
- requirements.txt — Python deps ready for Streamlit Cloud
- .gitignore, LICENSE

Read the in-app instructions for adding GCP credentials and testing with a sample invoice.
