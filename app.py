
# import streamlit as st
# import pandas as pd
# from PIL import Image
# import os
# import sys

# # --- Import ALL required functions from the utility file ---
# # NOTE: All these functions will be defined in scraper_utils.py (next section)
# from scraper_utils import (
#     fetch_all_results,
#     export_to_pdf,
#     sort_by_current_cgpa,
#     sort_by_latest_semester_grade,
#     # show_analytics # Commented out to avoid the previous TypeError
# )

# # Ensure current directory logic is safe for Streamlit Cloud
# try:
#     os.chdir(os.path.dirname(os.path.abspath(__file__)))
# except:
#     pass

# # --- UI Setup ---
# st.set_page_config(page_title="BEU Result Scraper (Direct Input)", layout="wide")
# st.markdown(
#     """
#     <div style='text-align:center; padding:15px; background-color:#003366; color:white; border-radius:10px;'>
#         <h2>Bihar Engineering University (BEU) Result Scraper</h2>
#         <h3>Developed By Gec Aurangabad</h3>
#     </div>
#     """,
#     unsafe_allow_html=True
# )
# st.title(" Direct Result Fetcher")


# # --- Input Form ---
# with st.form("result_form"):
    
#     # 1. Full URL Input (Crucial for Scraper to work)
#     default_url = "https://results.beup.ac.in/ResultsBTech4thSem2024_B2022Pub.aspx?Sem=IV&RegNo="
#     url_base = st.text_input(
#         "🔗 Enter Full Result URL Template (must end with ?RegNo=)", 
#         default_url
#     )
    
#     # 2. Registration Number Range
#     start_reg = st.number_input(" Start Registration Number", min_value=10000000000, step=1, value=22157147001, format="%d")
#     end_reg = st.number_input(" End Registration Number", min_value=10000000000, step=1, value=22157147005, format="%d")

#     st.markdown("---")
    
#     # 3. View/Export Options
#     view_mode = st.selectbox("View Mode", options=["regno", "cgpa", "semester"], format_func=lambda x: {
#         "regno": "Registration No. wise", "cgpa": "Sort by CGPA (High to Low)", "semester": "Sort by Latest Semester Grade"
#     }[x])
#     export_format = st.selectbox("Export Format", options=["pdf", "txt", "csv", "xlsx"], format_func=lambda x: x.upper())
    
#     submitted = st.form_submit_button(" Fetch Results")


# # --- Submission Logic ---
# if submitted:
#     if not url_base.endswith("RegNo=") and not url_base.endswith("RollNo="):
#         st.error(" कृपया URL Template को सही प्रारूप में दर्ज करें। यह `...aspx?RegNo=` पर समाप्त होना चाहिए।")
#         st.stop()
        
#     if start_reg >= end_reg:
#         st.error(" Start Registration No, End Registration No से कम होना चाहिए।")
#         st.stop()
    
#     st.info("Fetching results... This might take some time depending on the range.")
    
#     # --- Full Scrape ---
#     results = fetch_all_results(url_base, int(start_reg), int(end_reg))
    
#     if not results:
#         st.error(" Data Not Found. Please verify the URL Template and Registration Numbers.")
#         st.stop()

#     df = pd.DataFrame(results)

#     # 🌟 CRITICAL FIX: Convert CGPA to numeric before sorting 🌟
#     # This prevents the sorting functions from failing due to string/text data.
#     # 'errors="coerce"' replaces non-numeric values (like empty strings) with NaN.
#     df["Sem Cur. CGPA"] = pd.to_numeric(df["Sem Cur. CGPA"], errors="coerce")


#     # --- Sorting ---
#     if view_mode == "cgpa":
#         df = sort_by_current_cgpa(df)
#     elif view_mode == "semester":
#         df = sort_by_latest_semester_grade(df)

#     st.success(f"Results fetched successfully! Total {len(df)} records found.")
#     st.dataframe(df)
#     # The analytics function is currently commented out in the imports and here.
#     # To re-enable it, uncomment the imports and remove the TypeError by adding the numeric conversion there.


#     # --- Export options ---
#     export_path = f"results.{export_format}"
#     # ... (Export saving logic from previous code) ...
#     if export_format == "csv": df.to_csv(export_path, index=False)
#     elif export_format == "xlsx": df.to_excel(export_path, index=False, engine="openpyxl")
#     elif export_format == "txt": df.to_csv(export_path, sep="\t", index=False)
#     elif export_format == "pdf": export_to_pdf(df, export_path)
        
#     with open(export_path, "rb") as f:
#         st.download_button(label=f"Download {export_format.upper()}", data=f, file_name=export_path)
            
#     try: os.remove(export_path)
#     except OSError: pass
            
#     st.markdown("---")
#     st.markdown(
#         "<div style='text-align:center; font-size:14px; color:grey;'>"
#         "This tool relies on the public access method (GET request) used by the university. "
#         "</div>",
#         unsafe_allow_html=True
#     )




import streamlit as st
import pandas as pd
import os
import sys

# --- Import ALL required functions from the utility file ---
# We are importing functions from scraper_utils.py (which must be in a separate file)
from scraper_utils import (
    fetch_all_results,
    sort_by_current_cgpa,
    sort_by_latest_semester_grade,
    export_multi_sheet_excel,
    SGPA_CGPA_HEADERS # Import the necessary constant
)

# --- Configuration and Setup ---
try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except:
    pass

# --- Constants for Semester Data (Must match scraper_utils.py) ---
SGPA_CGPA_HEADERS = [
    "SGPA Sem I", "SGPA Sem II", "SGPA Sem III", "SGPA Sem IV",
    "SGPA Sem V", "SGPA Sem VI", "SGPA Sem VII", "SGPA Sem VIII",
    "Final CGPA"
]

#  FINAL LOGIC FOR GENERATING DYNAMIC URLS 🌟
def generate_url_templates():
    """Generates a comprehensive dictionary of all possible BEU result URLs based on batch and semester years."""
    URL_TEMPLATES = {}
    
    # Generate Batches from 2019 to 2030 (as requested)
    for start_year in range(2019, 2031):
        batch_label = f"{start_year}-{start_year + 4} Batch"
        URL_TEMPLATES[batch_label] = {}
        
        # Generate Semesters I to VIII
        for sem_num in range(1, 9):
            sem_roman = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII', 8: 'VIII'}[sem_num]
            
            # Current year for the exam in the URL string
            if sem_num in [1, 2]:
                exam_year = start_year + 0 # Sem I, II generally in the starting year
            elif sem_num in [3, 4]:
                exam_year = start_year + 1 # Sem III, IV generally in the year after start
            elif sem_num in [5, 6]:
                exam_year = start_year + 2 # Sem V, VI generally two years after start
            else:
                exam_year = start_year + 3 # Sem VII, VIII generally three years after start

            # Construct the dynamic URL part
            sem_part = f"BTech{sem_num}thSem{exam_year}_B{start_year}Pub"
            
            # Add to the dictionary (using the common /ResultsBTech pattern)
            URL_TEMPLATES[batch_label][f"Sem {sem_roman}"] = f"https://results.beup.ac.in/Results{sem_part}.aspx?Sem={sem_roman}&RegNo="

    return URL_TEMPLATES

ALL_URL_TEMPLATES = generate_url_templates()
# -----------------------------------------------------------------


# --- UI Setup ---
st.set_page_config(page_title="BEU Result Scraper (Direct Input)", layout="wide")
st.markdown(
    """
    <div style='text-align:center; padding:15px; background-color:#003366; color:white; border-radius:10px;'>
        <h2>Bihar Engineering University (BEU) Result Scraper</h2>
        <h3>Developed By Gec Aurangabad (Dynamic Batch & Semester)</h3>
    </div>
    """,
    unsafe_allow_html=True
)
st.title(" Welcome TO GEC Aurangabad Result Scraper")


# --- Input Form ---
with st.form("result_form"):
    
    # 🌟 NEW DYNAMIC DROPDOWNS 🌟
    selected_batch = st.selectbox("Select Batch", options=list(ALL_URL_TEMPLATES.keys()))
    
    # Get semesters available for the selected batch
    available_semesters = list(ALL_URL_TEMPLATES[selected_batch].keys())
    selected_semester = st.selectbox("Select Semester", options=available_semesters)
    
    # Automatically set the URL based on selection
    url_base = ALL_URL_TEMPLATES[selected_batch][selected_semester]

    st.markdown("---")
    st.info(f" URL (Check if live): `{url_base}`")
    
    start_reg = st.number_input(" Start Registration Number", min_value=10000000000, step=1, value=22157147001, format="%d")
    end_reg = st.number_input(" End Registration Number", min_value=10000000000, step=1, value=22157147005, format="%d")

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
    
    submitted = st.form_submit_button("  Fetch Results and View")


# --- Submission Logic ---
if submitted:
    
    # --- Input Validation ---
    if start_reg >= end_reg:
        st.error(" Start Registration No, End Registration No से कम होना चाहिए।")
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
    desired_cols += list(SGPA_CGPA_HEADERS)
    
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
        
        st.markdown("###  Summary Analytics")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Records Fetched", total_count)
        col2.metric("Pass Students (Zero Back)", passed_count)
        
        if not pd.isna(avg_cgpa):
             col3.metric("Average CGPA", f"{avg_cgpa:.2f}")
        else:
             col3.metric("Average CGPA", "N/A")

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