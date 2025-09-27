# scraper_utils.py
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import streamlit as st
import pandas as pd
import time
# from xhtml2pdf import pisa
from typing import Optional, Dict, Any, List

# --- Core Scraper Logic (Based on your successful GET requests) ---
def fetch_and_parse_result(base_url, registration_no, retries=1, backoff_factor=1):
    """Fetches result using the successful GET request structure: URL + RegNo."""
    # Base URL already contains the parameter name (e.g., ...?RegNo=), 
    # so we append the number directly.
    url = f"{base_url}{registration_no}" 
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Check for success marker
            if not soup.select_one("#ContentPlaceHolder1_DataList1_RegistrationNoLabel_0"):
                 return None

            result = {
                "Registration No.": soup.select_one("#ContentPlaceHolder1_DataList1_RegistrationNoLabel_0").text.strip(),
                "Student Name": soup.select_one("#ContentPlaceHolder1_DataList1_StudentNameLabel_0").text.strip(),
                "Father's Name": soup.select_one("#ContentPlaceHolder1_DataList1_FatherNameLabel_0").text.strip(),
                "Mother's Name": soup.select_one("#ContentPlaceHolder1_DataList1_MotherNameLabel_0").text.strip(),
                "Current SGPA": soup.select_one("#ContentPlaceHolder1_DataList5_GROSSTHEORYTOTALLabel_0").text.strip()
            }
            
            table = soup.select_one("#ContentPlaceHolder1_GridView3")
            if table:
                headers = [th.text.strip() for th in table.select("tr")[0].find_all("th")]
                values = [td.text.strip() for td in table.select("tr")[1].find_all("td")]
                for header, value in zip(headers, values):
                    result[f"Sem {header}"] = value
            
            result["Sem Cur. CGPA"] = result.get("Sem CGPA", "")
            return result
        except (requests.exceptions.RequestException, AttributeError):
            if attempt < retries - 1:
                time.sleep(backoff_factor * (2 ** attempt))
            return None


def fetch_all_results(base_url, start_reg, end_reg):
    results = []
    reg_numbers = list(range(start_reg, end_reg + 1))
    MAX_WORKERS = min(10, len(reg_numbers)) 
    
    progress_bar = st.progress(0)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_and_parse_result, base_url, reg_no): reg_no for reg_no in reg_numbers}
        
        for i, future in enumerate(futures):
            result = future.result()
            if result:
                results.append(result)
            
            progress_bar.progress((i + 1) / len(reg_numbers))
            
    progress_bar.empty()
    return results

# --- Analytics/Sorting Logic ---
def sort_by_current_cgpa(df):
    df["Sem Cur. CGPA"] = pd.to_numeric(df["Sem Cur. CGPA"], errors="coerce")
    return df.sort_values(by="Sem Cur. CGPA", ascending=False, na_position='last')

def sort_by_latest_semester_grade(df):
    sem_columns = [col for col in df.columns if col.startswith("Sem ")]
    def get_latest_grade(row):
        for col in reversed(sem_columns):
            try: return float(row[col])
            except: continue
        return -1
    df["Latest Semester Grade"] = df.apply(get_latest_grade, axis=1)
    sorted_df = df.sort_values(by="Latest Semester Grade", ascending=False).drop(columns=["Latest Semester Grade"])
    return sorted_df

def show_analytics(df):
    st.markdown("### Analytics Summary")
    st.info(f"Total students processed: {len(df)}")
    if "Sem Cur. CGPA" in df.columns:
        valid_cgpa = df["Sem Cur. CGPA"].dropna()
        if not valid_cgpa.empty:
            st.metric("Average CGPA", f"{valid_cgpa.mean():.2f}")
        else:
            st.warning("CGPA data not available for calculation.")

# --- PDF Export Logic ---
HTML_TEMPLATE = """...""" # Simplified for context

def export_to_pdf(df, output_file):
    # PDF generation ko filhaal disable kiya gaya hai
    st.error("❌ PDF export is temporarily disabled due to cloud deployment restrictions (xhtml2pdf issue).")
    
    # Iske bajaye, hum CSV file bana dete hain taaki download button kaam karta rahe
    try:
        df.to_csv(output_file, index=False, sep=',')
    except Exception as e:
        st.error(f"File export failed: {e}")