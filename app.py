import streamlit as st
import pandas as pd
from io import BytesIO
from ocr_utils import ocr_bytes, extract_summary_fields, extract_line_items
import base64

st.set_page_config(page_title="Invoice OCR → Excel", layout="centered")

st.title("Basic Invoice OCR → Excel")
st.write("Upload PDF or an image invoice, the app will OCR and extract basic invoice fields and a naive line-item table.")

uploaded = st.file_uploader("Upload invoice (PDF, PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"])

if uploaded is not None:
    with st.spinner("Running OCR..."):
        file_bytes = uploaded.read()
        text = ocr_bytes(file_bytes, uploaded.name)

    st.subheader("Raw OCR text (first 10 KB)")
    st.text_area("raw_text", value=text[:10000], height=300)

    st.subheader("Extracted Summary")
    summary = extract_summary_fields(text)
    summary_df = pd.DataFrame.from_records([summary])
    st.table(summary_df)

    st.subheader("Line Items (naive)")
    items = extract_line_items(text)
    if items:
        items_df = pd.DataFrame(items)
        st.dataframe(items_df)
    else:
        st.write("No line items detected by the simple heuristic.")

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
        label="Download Excel (Summary + LineItems)",
        data=excel_bytes,
        file_name="invoice_extraction.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # Also let user download raw OCR text
    st.download_button(
        label="Download raw OCR text",
        data=text.encode("utf-8"),
        file_name="invoice_ocr.txt",
        mime="text/plain",
    )

    st.success("Processing complete.")
else:
    st.info("Upload a PDF or image to start.")
