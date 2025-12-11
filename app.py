import streamlit as st
import pandas as pd
from io import BytesIO
import json
from ocr_utils import (
    vision_client_from_service_account_info,
    ocr_bytes,
    extract_summary_fields,
    extract_line_items,
)

st.set_page_config(page_title="Invoice OCR → Excel", layout="wide")

# --- Jazzy header ---
st.markdown(
    """
    <style>
    .header {display:flex; align-items:center; gap:16px;}
    .title {font-size:36px; font-weight:700; color:#0f172a;}
    .subtitle {color:#475569; margin-top:4px;}
    .card {background: linear-gradient(135deg,#f8fafc,#ecfeff); padding:14px; border-radius:12px;}
    </style>
    <div class="header">
      <div class="card">
        <div style="font-size:28px">🧾 Invoice OCR → Excel</div>
        <div class="subtitle">Upload invoices (PDF / PNG / JPG). OCR runs on Google Vision and output is downloadable as Excel.</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")

# --- Vision client setup ---
vision_client = None
if "GCP_CREDENTIALS_JSON" in st.secrets:
    try:
        sa_info = json.loads(st.secrets["GCP_CREDENTIALS_JSON"])
        vision_client = vision_client_from_service_account_info(sa_info)
        st.success("Google Cloud Vision credentials loaded from Streamlit secrets ✅")
    except Exception as e:
        st.error(f"Failed to create Vision client from secrets: {e}")
        st.info("Make sure your secret value is the raw JSON of the service account key.")
else:
    st.warning(
        "No Google Cloud Vision credentials found in Streamlit secrets.\n\n"
        "Add your service account JSON to Settings → Secrets with the key `GCP_CREDENTIALS_JSON`."
    )
    st.info("Without credentials the app cannot OCR. Provide credentials to enable OCR on Streamlit Cloud.")

st.write("")  # spacing

# --- Upload UI ---
with st.container():
    col1, col2 = st.columns([1, 2])
    with col1:
        uploaded = st.file_uploader("Upload invoice (PDF / PNG / JPG)", type=["pdf", "png", "jpg", "jpeg"])
        sample_checkbox = st.checkbox("Show sample invoice image", value=False)
    with col2:
        st.markdown(
            """
            #### How to use
            - Upload a scanned invoice PDF or an image.
            - The app uses Google Cloud Vision OCR (set credentials in Streamlit secrets).
            - Download results as Excel (Summary + LineItems).
            """
        )

if sample_checkbox:
    st.image("https://images.unsplash.com/photo-1555371363-6a84f798e9b3?q=80&w=1200&auto=format&fit=crop&ixlib=rb-4.0.3&s=3d7c0a5f9d4c9a3b9bfa4b3526b9b3a0", caption="Sample invoice (visual placeholder)", use_column_width=True)

if uploaded is not None:
    if vision_client is None:
        st.error("OCR disabled — please add Google Cloud Vision credentials to Streamlit secrets (GCP_CREDENTIALS_JSON).")
    else:
        with st.spinner("Running OCR via Google Vision..."):
            file_bytes = uploaded.read()
            text = ocr_bytes(file_bytes, uploaded.name, vision_client)

        st.markdown("### OCR Preview")
        st.code(text[:10000], language=None)

        st.markdown("### Extracted Summary")
        summary = extract_summary_fields(text)
        # present summary as metrics/cards
        s_col1, s_col2, s_col3, s_col4 = st.columns(4)
        s_col1.metric("Vendor", summary.get("vendor", "") or "—")
        s_col2.metric("Invoice #", summary.get("invoice_number", "") or "—")
        s_col3.metric("Date", summary.get("invoice_date", "") or "—")
        s_col4.metric("Total", summary.get("total", "") or "—")

        st.markdown("### Line Items (naive)")
        items = extract_line_items(text)
        if items:
            items_df = pd.DataFrame(items)
            st.dataframe(items_df, use_container_width=True)
        else:
            st.info("No line items detected by the simple heuristic.")

        # Prepare Excel
        def create_excel_bytes(summary_d, items_list):
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                pd.DataFrame.from_records([summary_d]).to_excel(writer, index=False, sheet_name="Summary")
                if items_list:
                    pd.DataFrame(items_list).to_excel(writer, index=False, sheet_name="LineItems")
            return output.getvalue()

        excel_bytes = create_excel_bytes(summary, items)
        st.download_button(
            label="Download Excel (Summary + LineItems) 📥",
            data=excel_bytes,
            file_name="invoice_extraction.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.download_button(
            label="Download raw OCR text (txt)",
            data=text.encode("utf-8"),
            file_name="invoice_ocr.txt",
            mime="text/plain",
        )

        st.success("Processing complete. If results look off, try a higher-resolution scan or different invoice sample.")
else:
    st.info("Upload a PDF or image invoice to begin.")

st.markdown("---")
st.markdown(
    """
    <div style="font-size:12px;color:#64748b">
    Note: This app uses Google Cloud Vision for OCR. Add your service account JSON to Streamlit Secrets with key `GCP_CREDENTIALS_JSON`.
    </div>
    """,
    unsafe_allow_html=True,
)
