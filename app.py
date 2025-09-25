import streamlit as st
import tempfile
import os
import extractor

# Set Streamlit page configuration
st.set_page_config(
    page_title="Odisha RoR Document Extractor",
    page_icon="📄",
    layout="wide"
)

# --- App Title and Description ---
st.title("📄 Odisha RoR Document Extractor")
st.markdown("This application extracts key information from Odia-language Records of Rights (RoR) PDF documents.")

# --- File Uploader ---
with st.sidebar:
    st.header("Configuration")
    st.info(f"Poppler path is set in `extractor.py` as:\n`{extractor.poppler_path}`")
    uploaded_file = st.file_uploader(
        "Upload a PDF or Image file",
        type=["pdf", "png", "jpg", "jpeg"],
        help="Please upload a scanned document in PDF or image format."
    )

# --- Main App Logic ---
if st.button("Extract Information", type="primary", use_container_width=True):
    if uploaded_file is not None:
        
        # Create a temporary directory to save the uploaded file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = os.path.join(temp_dir, uploaded_file.name)
            
            # Write the uploaded file to the temporary path
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.info(f"Processing '{uploaded_file.name}'...")
            
            try:
                # Use the wrapper function from your original code, passing the poppler path
                output = extractor.extract_ror_info(temp_file_path, poppler_path=extractor.poppler_path)
                
                if "❌" in output:
                    st.error(output.replace("❌", ""))
                else:
                    st.success("✅ Extraction complete!")
                    st.subheader("Extracted Details")
                    
                    # Split the output string into lines and display it as a list
                    for line in output.split("\n"):
                        if line.strip():
                            # Use Markdown to format the output
                            st.markdown(line)
                        
            except Exception as e:
                st.error(f"An error occurred: {e}")
                st.warning("Please ensure your Tesseract and Poppler installations are correct and paths are properly configured.")
    else:
        st.warning("⚠️ Please upload a document to proceed.")
