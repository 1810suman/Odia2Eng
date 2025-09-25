import streamlit as st
import tempfile
import os
from extractor import RoRDocumentExtractor

# --- Streamlit UI Setup ---
st.set_page_config(page_title="Odisha RoR Document Extractor", layout="wide")
st.title("📄 Odisha RoR Document Extractor")
st.markdown("This application extracts key information from Odia-language Records of Rights (RoR) PDF documents.")
st.write("---")

st.subheader("Configuration")
st.markdown("Poppler path is set in `extractor.py` as: `/usr/bin`")

# --- File Uploader ---
st.subheader("Upload a PDF or Image file")
uploaded_file = st.file_uploader(
    "Drag and drop file here",
    type=["pdf", "png", "jpg", "jpeg"]
)

if uploaded_file is not None:
    # Use a temporary file to save the uploaded PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.type.split('/')[-1]}") as temp_file:
        temp_file.write(uploaded_file.getvalue())
        temp_file_path = temp_file.name
        
    st.write(f"Processing '{uploaded_file.name}'...")
    
    # Process the file
    try:
        extractor = RoRDocumentExtractor()
        extracted_info = extractor.extract_info(temp_file_path)
        
        st.success("✅ Text extracted successfully!")
        
        # Display the extracted information
        st.write("### Extracted Information")
        for k, v in extracted_info.items():
            st.write(f"**{k}:** {v}")
            
    except Exception as e:
        st.error(f"❌ An error occurred during processing: {e}")
        st.error("Please ensure the file is a valid PDF and the required dependencies are correctly installed.")
    finally:
        # Clean up the temporary file
        os.remove(temp_file_path)
