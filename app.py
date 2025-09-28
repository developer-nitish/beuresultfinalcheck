 

import streamlit as st
import pandas as pd
import os
import sys
import datetime

# --- Import URL Config and Utility Functions ---
from url_config import ALL_URL_TEMPLATES, SGPA_CGPA_HEADERS, build_final_api_url
from scraper_utils import (
    fetch_all_results,
    sort_by_current_cgpa,
    sort_by_latest_semester_grade,
    export_multi_sheet_excel
)

# --- Configuration and Setup ---
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
        <h3>Developed By Gec Aurangabad (Final Working Version)</h3>
    </div>
    """,
    unsafe_allow_html=True
)
st.title(" 🤖 Direct Result Fetcher (Manual Year Control)")


# --- Input Form ---
with st.form("result_form"):
    
    # 🌟 NEW INPUTS: BATCH, SEMESTER, AND YEAR 🌟
    col_batch, col_sem = st.columns(2)
    with col_batch:
        selected_batch = st.selectbox("Select Batch", options=list(ALL_URL_TEMPLATES.keys()), index=5) 
    
    with col_sem:
        available_semesters = list(ALL_URL_TEMPLATES[selected_batch].keys())
        selected_semester = st.selectbox("Select Semester", options=available_semesters, index=0) 
    
    # --- Manual Exam Year Input (Defaults to next year for new batch) ---
    start_year = int(selected_batch.split('-')[0])
    # The 'next year' logic is safer than hardcoding 2025
    default_exam_year = start_year + 1 
    
    exam_year = st.number_input(
        " **Enter Exam Year (e.g., 2024)**", 
        min_value=2019, 
        max_value=datetime.date.today().year + 2, 
        value=default_exam_year,
        step=1
    )
    
    # Get the base template data
    template_data = ALL_URL_TEMPLATES[selected_batch][selected_semester]
    
    # Construct the final API URL using manual year (FIXED API BUILD HERE)
    url_base = build_final_api_url(template_data, exam_year)

    st.markdown("---")
    st.info(f" **API Template Used (Selected):** `{url_base}`")
    st.warning("**Note:** This API link must be **active** on the BEU server for the scrape to succeed.")


    # Registration numbers
    start_reg = st.number_input(" Start Registration Number", min_value=10000000000, step=1, value=24157147001, format="%d")
    end_reg = st.number_input(" End Registration Number", min_value=10000000000, step=1, value=24157147005, format="%d")

    st.markdown("---")
    
    # Dropdown for SORTING the data
    view_mode = st.selectbox("Sort By", options=["regno", "cgpa", "semester"], format_func=lambda x: {
        "regno": "Registration No. wise", "cgpa": "CGPA (High to Low)", "semester": "Latest Semester Grade"
    }[x])
    
    # Dropdown for FILTERING the displayed data
    view_format = st.selectbox("Result View Type", options=[
        "Condensed Result (All Students)", 
        "Fail Students Details",
        "Top Performers (CGPA > 7.0)",
        "Summary Analytics"
    ])
    
    # Export dropdown for multi-sheet Excel
    export_action = st.selectbox("Export Action", options=["Download Current View (CSV)", "Generate Multi-Sheet Excel (XLSX)"])
    
    submitted = st.form_submit_button(" 🚀 Fetch Results and View")


# --- Submission Logic ---
if submitted:
    
    # --- Input Validation ---
    if start_reg >= end_reg:
        st.error("Start Registration No, End Registration No से कम होना चाहिए।")
        st.stop()
    
    st.info("Fetching results... This might take some time depending on the range.")
    
    # --- Full Scrape ---
    results = fetch_all_results(url_base, int(start_reg), int(end_reg))
    
    if not results:
        st.error(f"Data Not Found. Please verify the Registration Numbers, or confirm that the template URL `{url_base}` is currently active and correct.")
        st.stop()

    df = pd.DataFrame(results)

    # Convert CGPA to numeric before sorting/filtering 
    df["CGPA"] = pd.to_numeric(df["CGPA"], errors="coerce")
    
    
    # --- 1. SORTING LOGIC ---
    if view_mode == "cgpa":
        df = sort_by_current_cgpa(df)
    elif view_mode == "semester":
        df = sort_by_latest_semester_grade(df)
    
    
    # --- 2. FILTERING LOGIC ---
    display_df = df.copy() 
    analytics_mode = False
    
    # FINAL COLS TO DISPLAY 
    desired_cols = [
        'Reg No', 'Name', 'Father', 'Mother', 'College', 'Course', 
        'Final CGPA', 'Back Paper Count'
    ]
    desired_cols += SGPA_CGPA_HEADERS
    
    # Detailed Subject Columns (Showing Code, Name, IA, ESE, Total, Grade for first 5 subjects)
    for i in range(1, 6): 
        desired_cols += [f'Sub{i} Code', f'Sub{i} Name', f'Sub{i} IA', f'Sub{i} ESE', f'Sub{i} Total', f'Sub{i} Grade'] 

    # Filter views (Logic remains correct)
    if view_format == "Fail Students Details":
        display_df = display_df[display_df['Back Paper Count'] > 0]
        if display_df.empty:
             st.warning("No students found with any back papers in this range.")

    elif view_format == "Top Performers (CGPA > 7.0)":
        top_threshold = 7.0
        display_df = display_df[display_df['CGPA'] >= top_threshold]
        if display_df.empty:
             st.warning("No students found with CGPA > 7.0.")

    elif view_format == "Summary Analytics":
        analytics_mode = True
        total_count = len(df)
        passed_count = len(df[df['Back Paper Count'] == 0])
        avg_cgpa = df['CGPA'].mean()
        
        st.markdown(" Summary Analytics")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Records Fetched", total_count)
        col2.metric("Pass Students (Zero Back)", passed_count)
        col3.metric("Average CGPA", f"{avg_cgpa:.2f}" if not pd.isna(avg_cgpa) else "N/A")

    # --- 3. DISPLAY & EXPORT ---
    if not analytics_mode:
        st.success(f"Results fetched successfully! Showing {len(display_df)} records for: {view_format}")
        
        # Ensure columns are unique and exist in the DataFrame
        unique_desired_cols = []
        seen = set()
        for col in desired_cols:
            if col not in seen:
                seen.add(col)
                unique_desired_cols.append(col)
                
        final_cols = [col for col in unique_desired_cols if col in display_df.columns]
        
        st.dataframe(display_df[final_cols], use_container_width=True)
        
    # --- Export Handler (Handles both CSV view and Multi-Sheet XLSX) ---
    export_path = "beu_results.xlsx" 
    
    if export_action == "Download Current View (CSV)":
        csv_data = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=f" Download Current View ({view_format}) as CSV",
            data=csv_data,
            file_name=f"{view_format.lower().replace(' ', '_')}.csv",
            mime='text/csv',
        )
    
    elif export_action == "Generate Multi-Sheet Excel (XLSX)":
        
        export_multi_sheet_excel(df, export_path)
        
        with open(export_path, "rb") as f:
            st.download_button(
                label=" Download Detailed Multi-Sheet Excel (XLSX)", 
                data=f, 
                file_name=export_path
            )
        try: os.remove(export_path)
        except OSError: pass


    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; font-size:14px; color:grey;'>"
        "This tool relies on the public access method (GET request) used by the university. "
        "</div>",
        unsafe_allow_html=True
    )