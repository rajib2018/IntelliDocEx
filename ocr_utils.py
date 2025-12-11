import io
import json
import re
from typing import List, Dict
from PIL import Image
import numpy as np

# PyMuPDF as fitz for rendering PDFs to images
import fitz  # PyMuPDF

# Google Vision
from google.cloud import vision
from google.oauth2 import service_account

# ---- OCR helpers ----

def vision_client_from_service_account_info(sa_info: dict):
    """
    Create a google.cloud.vision.ImageAnnotatorClient from service account info dict.
    """
    credentials = service_account.Credentials.from_service_account_info(sa_info)
    client = vision.ImageAnnotatorClient(credentials=credentials)
    return client


def pdf_to_images_via_fitz(pdf_bytes: bytes, zoom: float = 2.0) -> List[bytes]:
    """
    Convert PDF bytes to list of PNG bytes using PyMuPDF (fitz).
    zoom controls resolution (2.0 => ~150-200 dpi depending on source)
    """
    imgs = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    mat = fitz.Matrix(zoom, zoom)
    for page in doc:
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        imgs.append(img_bytes)
    doc.close()
    return imgs


def load_image_bytes(image_bytes: bytes) -> bytes:
    """
    Ensure image is a PNG/JPEG bytes suitable for Vision.
    If the uploaded bytes are already an image, we normalize them via PIL to PNG.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def ocr_image_with_vision_bytes(img_bytes: bytes, client: vision.ImageAnnotatorClient) -> str:
    """
    Use Google Vision Document/Text detection on image bytes.
    Returns extracted full text.
    """
    image = vision.Image(content=img_bytes)
    # Use document_text_detection for better layout and full text
    response = client.document_text_detection(image=image)
    if response.error.message:
        # fallback to text_detection if any error
        response = client.text_detection(image=image)
    # Try full_text_annotation when available
    text = ""
    if hasattr(response, "full_text_annotation") and response.full_text_annotation:
        text = response.full_text_annotation.text or ""
    else:
        # fallback
        anns = response.text_annotations
        if anns and len(anns) > 0:
            text = anns[0].description
    return text or ""


def ocr_bytes(file_bytes: bytes, filename: str, vision_client: vision.ImageAnnotatorClient) -> str:
    """
    Take uploaded bytes and run OCR using Google Vision. Handles PDF and images.
    """
    lower = filename.lower()
    text_pages = []
    if lower.endswith(".pdf"):
        images = pdf_to_images_via_fitz(file_bytes)
        for img_bytes in images:
            text_pages.append(ocr_image_with_vision_bytes(img_bytes, vision_client))
    else:
        img_bytes = load_image_bytes(file_bytes)
        text_pages.append(ocr_image_with_vision_bytes(img_bytes, vision_client))
    return "\n\n".join(text_pages)


# ---- Simple extraction heuristics ----

_DATE_RE = re.compile(
    r"((?:\d{1,2}[\/\-\.\s]\d{1,2}[\/\-\.\s]\d{2,4})|(?:\d{4}[\/\-\.\s]\d{1,2}[\/\-\.\s]\d{1,2}))"
)
_INVOICE_RE = re.compile(
    r"(?:Invoice\s*(?:No|Number|#)?[:\s]*|Inv(?:oice)?\s*#\s*)([A-Z0-9\-\/]+)",
    re.IGNORECASE,
)
_AMOUNT_RE = re.compile(r"([0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{2}))")
_LINE_ITEM_PRICE_RE = re.compile(r"\b([0-9]+(?:\.[0-9]{2}))\b")


def extract_summary_fields(text: str) -> Dict[str, str]:
    """Extract vendor (simple), invoice number, date, and total amount."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    vendor = ""
    invoice_no = ""
    invoice_date = ""
    total = ""

    # vendor: assume top non-empty line (but skip "invoice" words)
    for l in lines[:10]:
        if not re.search(r"invoice", l, re.IGNORECASE):
            vendor = l
            break
    if not vendor and lines:
        vendor = lines[0]

    # invoice number
    m = _INVOICE_RE.search(text)
    if m:
        invoice_no = m.group(1).strip()

    # date: first date-like token
    m2 = _DATE_RE.search(text)
    if m2:
        invoice_date = m2.group(1).strip()

    # total: look for lines containing 'total' or 'amount due', else pick largest money-like value
    total_candidates = []
    for l in lines:
        if re.search(r"(total|amount due|balance due|grand total)", l, re.IGNORECASE):
            mo = _AMOUNT_RE.search(l)
            if mo:
                total_candidates.append(mo.group(1))
    if not total_candidates:
        # fallback: collect all currency-like numbers then pick the largest
        all_amounts = _AMOUNT_RE.findall(text)
        if all_amounts:
            nums = []
            for a in all_amounts:
                try:
                    nums.append(float(a.replace(",", "").replace(" ", "")))
                except Exception:
                    pass
            if nums:
                total = f"{max(nums):.2f}"
        if not total and 'all_amounts' in locals() and all_amounts:
            total = all_amounts[-1]
    else:
        total = total_candidates[-1]

    total = total.replace(" ", "") if total else total

    return {
        "vendor": vendor,
        "invoice_number": invoice_no,
        "invoice_date": invoice_date,
        "total": total,
    }


def extract_line_items(text: str) -> List[Dict[str, str]]:
    """
    Very naive line-item extraction:
    - Finds lines that contain a price-like token and tries to split them into description and price.
    - Returns a list of dicts with keys: description, qty (if found), unit_price (if found), amount
    """
    items = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for l in lines:
        # Skip common header/footer lines that are unlikely to be items
        if re.search(r"(invoice|subtotal|total|amount due|tax|date|bill to|ship to)", l, re.IGNORECASE):
            continue
        prices = _LINE_ITEM_PRICE_RE.findall(l)
        if prices:
            amount = prices[-1]
            left = l.rsplit(amount, 1)[0].strip(" -\t")
            # attempt to find qty (single integer) in left
            qty = ""
            mqty = re.search(r"\b(\d+)\b", left)
            if mqty:
                qty = mqty.group(1)
                desc = left.replace(qty, "").strip()
            else:
                desc = left
            items.append({"description": desc, "qty": qty, "unit_price": "", "amount": amount})
    return items
