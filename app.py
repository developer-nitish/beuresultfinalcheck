import streamlit as st
import pandas as pd
from PIL import Image
import os
import sys

# --- Import ALL required functions from the utility file ---
# NOTE: All these functions will be defined in scraper_utils.py (next section)
from scraper_utils import (
    fetch_all_results,
    export_to_pdf,
    sort_by_current_cgpa,
    sort_by_latest_semester_grade,
    show_analytics
)

# Ensure current directory logic is safe for Streamlit Cloud
try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except:
    pass

# --- UI Setup ---
st.set_page_config(page_title="BEU Result Scraper (Direct Input)", layout="wide")
st.markdown(
    """
    <div style='text-align:center; padding:15px; background-color:#003366; color:white; border-radius:10px;'>
        <h2>Bihar Engineering University (BEU) Result Scraper</h2>
        <h3>Manual Link and Range Input (Cloud Ready)</h3>
    </div>
    """,
    unsafe_allow_html=True
)
st.title(" 🤖 Direct Result Fetcher")


# --- Input Form ---
with st.form("result_form"):
    
    # 1. Full URL Input (Crucial for Scraper to work)
    default_url = "https://results.beup.ac.in/ResultsBTech4thSem2024_B2022Pub.aspx?Sem=IV&RegNo="
    url_base = st.text_input(
        "🔗 Enter Full Result URL Template (must end with ?RegNo=)", 
        default_url
    )
    
    # 2. Registration Number Range
    start_reg = st.number_input("👉 Start Registration Number", min_value=10000000000, step=1, value=22157147001, format="%d")
    end_reg = st.number_input("👉 End Registration Number", min_value=10000000000, step=1, value=22157147005, format="%d")

    st.markdown("---")
    
    # 3. View/Export Options
    view_mode = st.selectbox("View Mode", options=["regno", "cgpa", "semester"], format_func=lambda x: {
        "regno": "Registration No. wise", "cgpa": "Sort by CGPA (High to Low)", "semester": "Sort by Latest Semester Grade"
    }[x])
    export_format = st.selectbox("Export Format", options=["pdf", "txt", "csv", "xlsx"], format_func=lambda x: x.upper())
    
    submitted = st.form_submit_button("🚀 Fetch Results")


# --- Submission Logic ---
if submitted:
    if not url_base.endswith("RegNo=") and not url_base.endswith("RollNo="):
        st.error("❌ कृपया URL Template को सही प्रारूप में दर्ज करें। यह `...aspx?RegNo=` पर समाप्त होना चाहिए।")
        st.stop()
        
    if start_reg >= end_reg:
        st.error("❌ Start Registration No, End Registration No से कम होना चाहिए।")
        st.stop()
    
    st.info("Fetching results... This might take some time depending on the range.")
    
    # --- Full Scrape ---
    results = fetch_all_results(url_base, int(start_reg), int(end_reg))
    
    if not results:
        st.error("❌ Data Not Found. Please verify the URL Template and Registration Numbers.")
        st.stop()

    df = pd.DataFrame(results)

    # --- Sorting ---
    if view_mode == "cgpa":
        df = sort_by_current_cgpa(df)
    elif view_mode == "semester":
        df = sort_by_latest_semester_grade(df)

    st.success(f"Results fetched successfully! Total {len(df)} records found.")
    st.dataframe(df)
    show_analytics(df)

    # --- Export options ---
    export_path = f"results.{export_format}"
    # ... (Export saving logic from previous code) ...
    if export_format == "csv": df.to_csv(export_path, index=False)
    elif export_format == "xlsx": df.to_excel(export_path, index=False, engine="openpyxl")
    elif export_format == "txt": df.to_csv(export_path, sep="\t", index=False)
    elif export_format == "pdf": export_to_pdf(df, export_path)
        
    with open(export_path, "rb") as f:
        st.download_button(label=f"📥 Download {export_format.upper()}", data=f, file_name=export_path)
            
    try: os.remove(export_path)
    except OSError: pass
            
    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; font-size:14px; color:grey;'>"
        "This tool relies on the public access method (GET request) used by the university. "
        "</div>",
        unsafe_allow_html=True
    )