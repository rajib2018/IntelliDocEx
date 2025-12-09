import streamlit as st
import pandas as pd
from PIL import Image
import io
import base64
import json
from datetime import datetime
import google.generativeai as genai

# Page configuration
st.set_page_config(
    page_title="Invoice OCR Extractor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for jazzy UI
st.markdown("""
<style>
    /* Main gradient background */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Card styling */
    .upload-card {
        background: rgba(255, 255, 255, 0.95);
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.18);
        margin-bottom: 2rem;
    }
    
    /* Header styling */
    .main-header {
        text-align: center;
        color: white;
        padding: 2rem 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-header h1 {
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        background: linear-gradient(120deg, #fff, #e0e7ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Success message */
    .success-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-weight: 600;
        margin: 1rem 0;
    }
    
    /* Download button styling */
    .stDownloadButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stDownloadButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* File uploader */
    [data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""

def extract_invoice_data(image, api_key):
    """Extract invoice data using Google Gemini Vision API"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = """
        Analyze this invoice image and extract ALL information in a structured JSON format.
        
        Return ONLY valid JSON (no markdown, no code blocks) with this exact structure:
        {
            "invoice_number": "string",
            "invoice_date": "string",
            "due_date": "string",
            "vendor_name": "string",
            "vendor_address": "string",
            "vendor_phone": "string",
            "vendor_email": "string",
            "customer_name": "string",
            "customer_address": "string",
            "customer_phone": "string",
            "customer_email": "string",
            "subtotal": "number",
            "tax_amount": "number",
            "tax_rate": "number",
            "discount": "number",
            "total_amount": "number",
            "currency": "string",
            "payment_terms": "string",
            "line_items": [
                {
                    "item_number": "string",
                    "description": "string",
                    "quantity": "number",
                    "unit_price": "number",
                    "total": "number"
                }
            ]
        }
        
        If any field is not present in the invoice, use null for that field.
        Ensure all numbers are numeric values, not strings.
        """
        
        response = model.generate_content([prompt, image])
        
        # Clean the response text
        response_text = response.text.strip()
        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        data = json.loads(response_text)
        return data, None
    
    except Exception as e:
        return None, str(e)

def create_excel_file(data):
    """Create Excel file from extracted data"""
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Invoice Details Sheet
        invoice_details = {
            'Field': ['Invoice Number', 'Invoice Date', 'Due Date', 
                     'Vendor Name', 'Vendor Address', 'Vendor Phone', 'Vendor Email',
                     'Customer Name', 'Customer Address', 'Customer Phone', 'Customer Email',
                     'Currency', 'Subtotal', 'Tax Rate', 'Tax Amount', 'Discount', 'Total Amount', 'Payment Terms'],
            'Value': [
                data.get('invoice_number'), data.get('invoice_date'), data.get('due_date'),
                data.get('vendor_name'), data.get('vendor_address'), data.get('vendor_phone'), data.get('vendor_email'),
                data.get('customer_name'), data.get('customer_address'), data.get('customer_phone'), data.get('customer_email'),
                data.get('currency'), data.get('subtotal'), data.get('tax_rate'), data.get('tax_amount'), 
                data.get('discount'), data.get('total_amount'), data.get('payment_terms')
            ]
        }
        df_details = pd.DataFrame(invoice_details)
        df_details.to_excel(writer, sheet_name='Invoice Details', index=False)
        
        # Line Items Sheet
        if data.get('line_items'):
            df_items = pd.DataFrame(data['line_items'])
            df_items.to_excel(writer, sheet_name='Line Items', index=False)
    
    output.seek(0)
    return output

# Main UI
st.markdown('<div class="main-header"><h1>📄 Invoice OCR Extractor</h1><p>Extract invoice data with AI-powered precision</p></div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    api_key = st.text_input("Google Gemini API Key", type="password", value=st.session_state.api_key)
    
    if api_key:
        st.session_state.api_key = api_key
        st.success("✅ API Key configured")
    else:
        st.info("🔑 Enter your Gemini API key to start")
        st.markdown("[Get API Key](https://makersuite.google.com/app/apikey)")
    
    st.markdown("---")
    st.markdown("### 📋 Features")
    st.markdown("""
    - ✨ AI-powered extraction
    - 📊 Excel export
    - 🎯 High accuracy
    - ⚡ Fast processing
    - 🔒 Secure & private
    """)
    
    st.markdown("---")
    st.markdown("### 💡 Tips")
    st.markdown("""
    - Upload clear images
    - Supported: JPG, PNG, PDF
    - Max size: 200MB
    """)

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown("### 📤 Upload Invoice")
    
    uploaded_file = st.file_uploader(
        "Choose an invoice image",
        type=['png', 'jpg', 'jpeg', 'pdf'],
        help="Upload a clear image of your invoice"
    )
    
    if uploaded_file:
        # Display image
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Invoice", use_container_width=True)
        
        # Extract button
        if st.button("🚀 Extract Data", use_container_width=True, type="primary"):
            if not st.session_state.api_key:
                st.error("❌ Please enter your Google Gemini API key in the sidebar")
            else:
                with st.spinner("🔍 Analyzing invoice..."):
                    data, error = extract_invoice_data(image, st.session_state.api_key)
                    
                    if error:
                        st.error(f"❌ Error: {error}")
                    else:
                        st.session_state.extracted_data = data
                        st.markdown('<div class="success-box">✅ Data extracted successfully!</div>', unsafe_allow_html=True)
                        st.balloons()
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="upload-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Extracted Data")
    
    if st.session_state.extracted_data:
        data = st.session_state.extracted_data
        
        # Display key information in tabs
        tab1, tab2, tab3 = st.tabs(["📝 Summary", "📦 Line Items", "💰 Totals"])
        
        with tab1:
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Invoice #", data.get('invoice_number', 'N/A'))
                st.metric("Vendor", data.get('vendor_name', 'N/A'))
            with col_b:
                st.metric("Date", data.get('invoice_date', 'N/A'))
                st.metric("Customer", data.get('customer_name', 'N/A'))
        
        with tab2:
            if data.get('line_items'):
                df = pd.DataFrame(data['line_items'])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No line items found")
        
        with tab3:
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Subtotal", f"{data.get('currency', '$')} {data.get('subtotal', 0)}")
            with col_b:
                st.metric("Tax", f"{data.get('currency', '$')} {data.get('tax_amount', 0)}")
            with col_c:
                st.metric("Total", f"{data.get('currency', '$')} {data.get('total_amount', 0)}")
        
        # Download button
        st.markdown("---")
        excel_file = create_excel_file(data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        st.download_button(
            label="⬇️ Download Excel Report",
            data=excel_file,
            file_name=f"invoice_extract_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.info("👆 Upload an invoice and click 'Extract Data' to see results here")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: white; padding: 1rem;'>"
    "Made with ❤️ using Streamlit & Google Gemini AI"
    "</div>",
    unsafe_allow_html=True
)
