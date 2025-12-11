import io
import re
from typing import List, Dict, Tuple
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes
import numpy as np


def pdf_to_images(pdf_bytes: bytes, dpi: int = 300) -> List[Image.Image]:
    """Convert PDF bytes to list of PIL Images (one per page)."""
    images = convert_from_bytes(pdf_bytes, dpi=dpi)
    return images


def ocr_image(img: Image.Image, lang: str = "eng") -> str:
    """Run Tesseract OCR on a PIL Image and return extracted text."""
    text = pytesseract.image_to_string(img, lang=lang)
    return text


def ocr_bytes(file_bytes: bytes, filename: str) -> str:
    """Take uploaded bytes and run OCR (handles pdf and images)."""
    lower = filename.lower()
    text_pages = []
    if lower.endswith(".pdf"):
        images = pdf_to_images(file_bytes)
        for img in images:
            text_pages.append(ocr_image(img))
    else:
        # treat as image
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        text_pages.append(ocr_image(img))
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
            # normalize comma thousands
            nums = [float(a.replace(",", "").replace(" ", "")) for a in all_amounts]
            if nums:
                total = f"{max(nums):.2f}"
        if not total and all_amounts:
            total = all_amounts[-1]
    else:
        total = total_candidates[-1]

    # normalize total (remove spaces)
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
            # choose rightmost price as amount
            amount = prices[-1]
            left = l.rsplit(amount, 1)[0].strip(" -\t")
            # attempt to find qty (single integer) in left
            qty = ""
            mqty = re.search(r"\b(\d+)\b", left)
            if mqty:
                qty = mqty.group(1)
                # remove qty from description
                desc = left.replace(qty, "").strip()
            else:
                desc = left
            items.append({"description": desc, "qty": qty, "unit_price": "", "amount": amount})
    return items
