
# # scraper_utils.py
# import requests
# from bs4 import BeautifulSoup
# from concurrent.futures import ThreadPoolExecutor
# import streamlit as st
# import pandas as pd
# import time
# from typing import Optional, Dict, Any, List

# # --- New Imports for Selenium/Excel Logic ---
# # Aapko in libraries ko apne requirements.txt mein dobara add karna padega:
# import openpyxl
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# import os
# # -------------------------------------------


# # --- Helper Function for Selenium (Required by run_scraper) ---
# def extract_subjects(table_id, subject_type, driver):
#     """Extracts subject details from the given table ID using Selenium."""
#     subjects = []
#     try:
#         table = driver.find_element(By.ID, table_id)
#         rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header row
        
#         for row in rows:
#             cols = row.find_elements(By.TAG_NAME, "td")
#             if len(cols) >= 8: # Assuming the structure is: Code, Name, IA, ESE, Total, Grade, Credit
#                 subjects.append({
#                     "code": cols[0].text.strip(),
#                     "name": cols[1].text.strip(),
#                     "type": subject_type,
#                     "ia": cols[2].text.strip(),
#                     "ese": cols[3].text.strip(),
#                     "total": cols[4].text.strip(),
#                     "grade": cols[5].text.strip(),
#                     "credit": cols[6].text.strip()
#                 })
#     except Exception:
#         pass
#     return subjects


# # --- Core Scraper Logic (Request/BS4 - Used by app.py) ---
# def fetch_and_parse_result(base_url, registration_no, retries=1, backoff_factor=1):
#     # ... (Your existing requests/BS4 function body remains here) ...
#     # This function is used by fetch_all_results in your app.py
#     # ... (Rest of the function body) ...
#     """Fetches result using the successful GET request structure: URL + RegNo."""
#     url = f"{base_url}{registration_no}" 
    
#     headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
#     for attempt in range(retries):
#         try:
#             response = requests.get(url, headers=headers, timeout=10)
#             response.raise_for_status()
#             soup = BeautifulSoup(response.text, "html.parser")
            
#             # Check for success marker
#             if not soup.select_one("#ContentPlaceHolder1_DataList1_RegistrationNoLabel_0"):
#                  return None

#             result = {
#                 "Registration No.": soup.select_one("#ContentPlaceHolder1_DataList1_RegistrationNoLabel_0").text.strip(),
#                 "Student Name": soup.select_one("#ContentPlaceHolder1_DataList1_StudentNameLabel_0").text.strip(),
#                 "Father's Name": soup.select_one("#ContentPlaceHolder1_DataList1_FatherNameLabel_0").text.strip(),
#                 "Mother's Name": soup.select_one("#ContentPlaceHolder1_DataList1_MotherNameLabel_0").text.strip(),
#                 "Current SGPA": soup.select_one("#ContentPlaceHolder1_DataList5_GROSSTHEORYTOTALLabel_0").text.strip()
#             }
            
#             table = soup.select_one("#ContentPlaceHolder1_GridView3")
#             if table:
#                 headers = [th.text.strip() for th in table.select("tr")[0].find_all("th")]
#                 values = [td.text.strip() for td in table.select("tr")[1].find_all("td")]
#                 for header, value in zip(headers, values):
#                     result[f"Sem {header}"] = value
            
#             result["Sem Cur. CGPA"] = result.get("Sem CGPA", "")
#             return result
#         except (requests.exceptions.RequestException, AttributeError):
#             if attempt < retries - 1:
#                 time.sleep(backoff_factor * (2 ** attempt))
#             return None


# def fetch_all_results(base_url, start_reg, end_reg):
#     # ... (Your existing function body remains here) ...
#     # This function is not used by the main() function from the first block
#     # ... (Rest of the function body) ...
#     results = []
#     reg_numbers = list(range(start_reg, end_reg + 1))
#     MAX_WORKERS = min(10, len(reg_numbers)) 
    
#     progress_bar = st.progress(0)
    
#     with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
#         futures = {executor.submit(fetch_and_parse_result, base_url, reg_no): reg_no for reg_no in reg_numbers}
        
#         for i, future in enumerate(futures):
#             result = future.result()
#             if result:
#                 results.append(result)
            
#             progress_bar.progress((i + 1) / len(reg_numbers))
            
#     progress_bar.empty()
#     return results


# # --- Analytics/Sorting Logic (Your existing functions) ---
# def sort_by_current_cgpa(df):
#     df["Sem Cur. CGPA"] = pd.to_numeric(df["Sem Cur. CGPA"], errors="coerce")
#     return df.sort_values(by="Sem Cur. CGPA", ascending=False, na_position='last')

# def sort_by_latest_semester_grade(df):
#     sem_columns = [col for col in df.columns if col.startswith("Sem ")]
#     def get_latest_grade(row):
#         for col in reversed(sem_columns):
#             try: return float(row[col])
#             except: continue
#         return -1
#     df["Latest Semester Grade"] = df.apply(get_latest_grade, axis=1)
#     sorted_df = df.sort_values(by="Latest Semester Grade", ascending=False).drop(columns=["Latest Semester Grade"])
#     return sorted_df

# def show_analytics(df):
#     st.markdown("### Analytics Summary")
#     st.info(f"Total students processed: {len(df)}")
#     if "Sem Cur. CGPA" in df.columns:
#         valid_cgpa = df["Sem Cur. CGPA"].dropna()
#         if not valid_cgpa.empty:
#             st.metric("Average CGPA", f"{valid_cgpa.mean():.2f}")
#         else:
#             st.warning("CGPA data not available for calculation.")

# # --- PDF Export Logic ---
# def export_to_pdf(df, output_file):
#     st.error(" PDF export is temporarily disabled due to cloud deployment restrictions (xhtml2pdf issue).")
#     try:
#         df.to_csv(output_file, index=False, sep=',')
#     except Exception as e:
#         st.error(f"File export failed: {e}")


# # --- NEW: Selenium/Excel Logic (From the first block) ---
# def run_scraper(start_reg, end_reg, url):
#     """
#     Main scraping function using Selenium and exporting data to openpyxl.
#     NOTE: This is not ideal for Streamlit Cloud and requires specific setup.
#     """
#     # Initialize Chrome Driver (Requires specific setup for Streamlit Cloud)
#     options = webdriver.ChromeOptions()
#     options.add_argument("--headless")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     driver = webdriver.Chrome(options=options)
    
#     # ------------------- OPENPYXL SETUP -------------------
#     wb = openpyxl.Workbook()
#     ws_main = wb.active
#     ws_main.title = "Condensed Result"
#     ws_failures = wb.create_sheet("Subject-wise Failures Students")
#     ws_topper = wb.create_sheet("Low Achievers Students")
#     ws_failstudents = wb.create_sheet("Fail Student Details Students")
#     ws_backlog = wb.create_sheet("All Backlog Summary")
#     ws_sgpa_summary = wb.create_sheet("SGPA Summary")

#     headers = ["Reg No", "Name", "Father", "Mother", "College", "Course", "Semester"]
#     for i in range(1, 16):
#         headers += [f"Sub{i} Code", f"Sub{i} Name", f"Sub{i} Type", "IA", "ESE", "Total", "Grade", "Credit"]
#     headers += ["SGPA Sem I", "Sem II", "Sem III", "Sem IV", "Sem V", "Sem VI", "Sem VII", "Sem VIII", "CGPA", "Remarks", "Publish Date"]

#     ws_main.append(headers)
#     ws_failures.append(["Subject Code", "Subject Name", "Student Reg No", "Student Name", "Semester", "Grade", "Type"])
#     ws_topper.append(["Reg No", "Name", "CGPA"])
#     ws_failstudents.append(headers)
#     ws_sgpa_summary.append(["SGPA Range", "Student Count"])

#     fail_count = 0
#     backlog_counter = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, '5+': 0}
#     sgpa_ranges = {">9.0": 0, "8.0-9.0": 0, "7.0-8.0": 0, "6.0-7.0": 0, "5.0-6.0": 0}

#     reg_numbers = [str(i) for i in range(start_reg, end_reg + 1)]
#     # ------------------- OPENPYXL SETUP END -------------------

#     for reg in reg_numbers:
#         st.write(f"Checking {reg}")
#         try:
#             # --- Selenium Navigation ---
#             driver.get(url)
#             WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_TextBox_RegNo")))

#             driver.find_element(By.ID, "ContentPlaceHolder1_TextBox_RegNo").send_keys(reg)
#             driver.find_element(By.ID, "ContentPlaceHolder1_Button_Show").click()
#             WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_DataList1")))
#             # ---------------------------

#             # --- Data Extraction ---
#             name = driver.find_element(By.ID, "ContentPlaceHolder1_DataList1_StudentNameLabel_0").text.strip()
#             father = driver.find_element(By.ID, "ContentPlaceHolder1_DataList1_FatherNameLabel_0").text.strip()
#             mother = driver.find_element(By.ID, "ContentPlaceHolder1_DataList1_MotherNameLabel_0").text.strip()
#             college = driver.find_element(By.ID, "ContentPlaceHolder1_DataList1_CollegeNameLabel_0").text.strip()
#             course = driver.find_element(By.ID, "ContentPlaceHolder1_DataList1_CourseLabel_0").text.strip()
#             semester = driver.find_element(By.ID, "ContentPlaceHolder1_DataList2_Exam_Name_0").text.strip()

#             sgpa_table = driver.find_element(By.ID, "ContentPlaceHolder1_GridView3")
#             sgpa_values = sgpa_table.find_elements(By.TAG_NAME, "tr")[1].find_elements(By.TAG_NAME, "td")
#             sgpas = [cell.text.strip() for cell in sgpa_values[:8]]
#             cgpa = sgpa_values[8].text.strip()
#             sgpas += ["NA"] * (8 - len(sgpas))

#             try:
#                 remark = driver.find_element(By.ID, "ContentPlaceHolder1_DataList3_remarkLabel_0").text.strip()
#             except:
#                 remark = ""

#             try:
#                 pub_date_element = driver.find_element(By.XPATH, "//table[@id='ContentPlaceHolder1_DataList3']//tr[2]/td")
#                 pub_date = pub_date_element.text.split(":")[-1].strip()
#             except:
#                 pub_date = ""

#             theory = extract_subjects("ContentPlaceHolder1_GridView1", "Theory", driver)
#             practical = extract_subjects("ContentPlaceHolder1_GridView2", "Practical", driver)
#             subjects = theory + practical
#             # ---------------------------

#             # --- Excel/Analytics Population ---
#             row = [reg, name, father, mother, college, course, semester]
#             fail_count_student = 0

#             for sub in subjects:
#                 row += [sub["code"], sub["name"], sub["type"], sub["ia"], sub["ese"], sub["total"], sub["grade"], sub["credit"]]
#                 if sub["grade"].upper() == "F":
#                     fail_count_student += 1
#                     ws_failures.append([sub["code"], sub["name"], reg, name, semester, sub["grade"], sub["type"]])

#             while len(subjects) < 15:
#                 row += ["", "", "", "", "", "", "", ""]
#                 subjects.append(None)

#             row += sgpas + [cgpa, remark, pub_date]
#             ws_main.append(row)

#             if fail_count_student > 0:
#                 ws_failstudents.append(row)
#                 fail_count += 1

#             try:
#                 # CGPA check for Topper sheet (Renamed to Low Achievers in the sheet title, but logic looks like Topper)
#                 if float(cgpa) >= 5.0: # Assuming 5.0 is the threshold
#                     ws_topper.append([reg, name, cgpa])
#             except:
#                 pass

#             if fail_count_student in backlog_counter:
#                 backlog_counter[fail_count_student] += 1
#             else:
#                 backlog_counter['5+'] += 1

#             try:
#                 # Assuming current SGPA is at index 3 (Sem IV)
#                 current_sgpa = float(sgpas[3]) 
#                 if current_sgpa > 9.0:
#                     sgpa_ranges[">9.0"] += 1
#                 elif 8.0 <= current_sgpa <= 9.0:
#                     sgpa_ranges["8.0-9.0"] += 1
#                 elif 7.0 <= current_sgpa < 8.0:
#                     sgpa_ranges["7.0-8.0"] += 1
#                 elif 6.0 <= current_sgpa < 7.0:
#                     sgpa_ranges["6.0-7.0"] += 1
#                 elif 5.0 <= current_sgpa < 6.0:
#                     sgpa_ranges["5.0-6.0"] += 1
#             except:
#                 pass

#         except Exception as e:
#             # Error logging
#             st.error(f" Failed: {reg} - {e}")
#             with open(f"debug_{reg}.html", "w", encoding="utf-8") as f:
#                 f.write(driver.page_source)
#     # ---------------------------------------------
    
#     # --- Final Excel Summary ---
#     ws_failstudents.append([])
#     ws_failstudents.append([" Total Failed Students", fail_count])

#     ws_backlog.append(["Backlog Count", "Number of Students"])
#     for k in [0, 1, 2, 3, 4, '5+']:
#         ws_backlog.append([f"{k} Backlogs" if k != 0 else "Zero Backlog", backlog_counter[k]])

#     for k, v in sgpa_ranges.items():
#         ws_sgpa_summary.append([k, v])

#     driver.quit()

#     base_name = "beu_result"
#     counter = 0
#     while os.path.exists(f"{base_name}_{counter}.xlsx"):
#         counter += 1
#     filename = f"{base_name}_{counter}.xlsx"

#     wb.save(filename)
#     st.success(f" All done! Result saved as {filename}")
#     with open(filename, "rb") as f:
#         st.download_button(" Download Excel File", f, file_name=filename)
#     # ---------------------------------------------

# # --- NEW: Main UI Function (From the first block) ---
# def main():
#     """Defines the main Streamlit UI for the Selenium scraper."""
#     st.set_page_config(page_title="BEU Result Scraper", layout="centered")

#     # ===== HEADER =====
#     st.markdown(
#         """
#         <div style="text-align:center; padding:15px; background-color:#003366; color:white; border-radius:10px;">
#             <h2>Bihar Engineering University (BEU), Patna</h2>
#             <h3>Automated Result Scraper Tool</h3>
#             <p>Fetch, Parse & Export Results to Excel/CSV – Fast, Reliable & Configurable</p>
#         </div>
#         """,
#         unsafe_allow_html=True
#     )

#     st.title(" BEU Result Scraper Tool")

#     url = st.text_input("🔗 Enter BEU Result URL", "https://results.beup.ac.in/BTech4thSem2024_B2022Results.aspx")
#     start_reg = st.number_input("Start Registration Number", min_value=10000000000, step=1)
#     end_reg = st.number_input("End Registration Number", min_value=10000000000, step=1)

#     if st.button("Start Scraping"):
#         if start_reg > end_reg:
#             st.error(" Start Reg. No must be less than End Reg. No")
#         else:
#             # Calls the run_scraper function defined above
#             run_scraper(int(start_reg), int(end_reg), url)

#     # ===== FOOTER =====
#     st.markdown(
#         """
#         <hr>
#         <div style="text-align:center; font-size:14px; padding:10px;">
#             <p>💻 Developed by <b>GEC Aurangabad</b></p>
#             <p>
#                  <a href="https://github.com/developer-nitish" target="_blank">GitHub</a> | 
#                  <a href="https://www.linkedin.com" target="_blank">LinkedIn</a> | 
#                 <a href="https://twitter.com" target="_blank">Twitter</a>
#             </p>
#         </div>
#         """,
#         unsafe_allow_html=True
#     )

# # Agar aap chahte hain ki yeh file Streamlit par main file ki tarah run ho
# # if __name__ == "__main__":
# #     main()





# import requests
# from bs4 import BeautifulSoup
# from concurrent.futures import ThreadPoolExecutor
# import streamlit as st
# import pandas as pd
# import time
# from typing import Optional, Dict, Any, List

# # --- Imports for Multi-Sheet Excel ---
# import openpyxl
# from openpyxl.utils.dataframe import dataframe_to_rows
# # -------------------------------------

# # --- Constants for Semester Data ---
# SGPA_CGPA_HEADERS = [
#     "SGPA Sem I", "SGPA Sem II", "SGPA Sem III", "SGPA Sem IV",
#     "SGPA Sem V", "SGPA Sem VI", "SGPA Sem VII", "SGPA Sem VIII",
#     "Final CGPA"
# ]


# # --- Core Scraper Logic (Requests/BS4) ---
# def fetch_and_parse_result(base_url, registration_no, retries=1, backoff_factor=1):
#     """Fetches result for a single registration number, extracts ALL details including subject marks and all semester SGPAs/CGPAs."""
#     url = f"{base_url}{registration_no}" 
#     headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
#     for attempt in range(retries):
#         try:
#             response = requests.get(url, headers=headers, timeout=10)
#             response.raise_for_status()
#             soup = BeautifulSoup(response.text, "html.parser")
            
#             # 1. Check for success marker
#             if not soup.select_one("#ContentPlaceHolder1_DataList1_RegistrationNoLabel_0"):
#                  return None

#             result = {
#                 "Reg No": soup.select_one("#ContentPlaceHolder1_DataList1_RegistrationNoLabel_0").text.strip(),
#                 "Name": soup.select_one("#ContentPlaceHolder1_DataList1_StudentNameLabel_0").text.strip(),
#                 "Father": soup.select_one("#ContentPlaceHolder1_DataList1_FatherNameLabel_0").text.strip(),
#                 "Mother": soup.select_one("#ContentPlaceHolder1_DataList1_MotherNameLabel_0").text.strip(),
#                 "College": soup.select_one("#ContentPlaceHolder1_DataList1_CollegeNameLabel_0").text.strip(),
#                 "Course": soup.select_one("#ContentPlaceHolder1_DataList1_CourseLabel_0").text.strip(),
#                 "Back Paper Count": 0,
#                 "Detailed Subjects List": [] 
#             }
            
#             # --- 2. Extract All Semester SGPAs/CGPA (GridView3) ---
#             sgpa_table = soup.select_one("#ContentPlaceHolder1_GridView3")
            
#             for header in SGPA_CGPA_HEADERS: result[header] = 'NA'
#             result["CGPA"] = 'NA'

#             if sgpa_table:
#                 sgpa_values = sgpa_table.find_all("tr")[-1].find_all("td")
                
#                 if len(sgpa_values) >= 9:
#                     for i, header in enumerate(SGPA_CGPA_HEADERS):
#                          result[header] = sgpa_values[i].text.strip()
                    
#                     result["CGPA"] = result["Final CGPA"]
            
            
#             # --- 3. Detailed Subject Tables Scraping (Including IA/ESE) ---
            
#             def extract_subjects_from_table(table_id, subject_type):
#                 subjects = []
#                 table = soup.select_one(f"#{table_id}")
#                 if table:
#                     rows = table.find_all("tr")[1:] 
#                     for row in rows:
#                         cols = row.find_all("td")
#                         if len(cols) >= 8:
#                             subjects.append({
#                                 "Code": cols[0].text.strip(),
#                                 "Name": cols[1].text.strip(),
#                                 "Type": subject_type,
#                                 "IA": cols[3].text.strip(), 
#                                 "ESE": cols[2].text.strip(),
#                                 "Total": cols[4].text.strip(),
#                                 "Grade": cols[5].text.strip(),
#                                 "Credit": cols[6].text.strip()
#                             })
#                 return subjects

#             all_subjects = extract_subjects_from_table("ContentPlaceHolder1_GridView1", "Theory") 
#             all_subjects += extract_subjects_from_table("ContentPlaceHolder1_GridView2", "Practical")
            
#             back_count = 0
            
#             # Flatten detailed subjects for the main DataFrame/Excel output
#             for i, sub in enumerate(all_subjects):
#                 result["Detailed Subjects List"].append(sub)
                
#                 # Add columns to main result for display
#                 for key in ["Code", "Name", "Type", "IA", "ESE", "Total", "Grade", "Credit"]:
#                     result[f"Sub{i+1} {key}"] = sub[key]
                
#                 if sub["Grade"].upper() == "F":
#                     back_count += 1

#             result["Back Paper Count"] = back_count
            
#             # Fill remaining columns up to 15 subjects 
#             for i in range(len(all_subjects), 15):
#                 for key in ["Code", "Name", "Type", "IA", "ESE", "Total", "Grade", "Credit"]:
#                     result[f"Sub{i+1} {key}"] = ""
            
#             return result
        
#         except (requests.exceptions.RequestException, AttributeError, ValueError) as e:
#             if attempt < retries - 1:
#                 time.sleep(backoff_factor * (2 ** attempt))
#             return None


# def fetch_all_results(base_url, start_reg, end_reg):
#     results = []
#     reg_numbers = list(range(start_reg, end_reg + 1))
#     MAX_WORKERS = min(10, len(reg_numbers)) 
    
#     progress_bar = st.progress(0)
    
#     with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
#         futures = {executor.submit(fetch_and_parse_result, base_url, reg_no): reg_no for reg_no in reg_numbers}
        
#         for i, future in enumerate(futures):
#             result = future.result()
#             if result:
#                 results.append(result)
            
#             progress_bar.progress((i + 1) / len(reg_numbers))
            
#     progress_bar.empty()
#     return results


# # --- Sorting Logic ---
# def sort_by_current_cgpa(df):
#     df["CGPA"] = pd.to_numeric(df["CGPA"], errors="coerce")
#     return df.sort_values(by="CGPA", ascending=False, na_position='last')

# def sort_by_latest_semester_grade(df):
#     df_sorted = df.copy()
    
#     for header in reversed(SGPA_CGPA_HEADERS[:-1]): 
#         df_sorted[header] = pd.to_numeric(df_sorted[header], errors='coerce')
        
#     latest_sgpa_column = None
#     for header in reversed(SGPA_CGPA_HEADERS[:-1]):
#         if not df_sorted[header].isna().all():
#             latest_sgpa_column = header
#             break
            
#     if latest_sgpa_column:
#         return df_sorted.sort_values(by=latest_sgpa_column, ascending=False, na_position='last')
#     else:
#         return sort_by_current_cgpa(df)


# # --- Multi-Sheet Excel Export Function ---
# def export_multi_sheet_excel(df: pd.DataFrame, output_file: str):
#     """
#     Creates the multi-sheet Excel report with detailed breakdown matching your requirements.
#     """
#     st.info("Generating detailed multi-sheet Excel report (XLSX)...")
    
#     wb = openpyxl.Workbook()
#     df_cleaned = df.copy()
#     df_cleaned["CGPA"] = pd.to_numeric(df_cleaned["CGPA"], errors="coerce")

#     # --- Sheet Creation ---
#     ws_main = wb.active
#     ws_main.title = "Condensed Result"
#     ws_failures = wb.create_sheet("Subject-wise Failures Students")
#     ws_topper = wb.create_sheet("Low Achievers Students") 
#     ws_failstudents = wb.create_sheet("Fail Student Details Students")
#     ws_backlog = wb.create_sheet("All Backlog Summary")
#     ws_sgpa_summary = wb.create_sheet("SGPA Summary")
    
#     # --- Headers for Main and Fail Details Sheets ---
#     subject_fields = []
#     for i in range(1, 16):
#         subject_fields += [f"Sub{i} Code", f"Sub{i} Name", f"Sub{i} Type", f"Sub{i} IA", f"Sub{i} ESE", f"Sub{i} Total", f"Sub{i} Grade", f"Sub{i} Credit"]

#     main_headers = ["Reg No", "Name", "Father", "Mother", "College", "Course"] + SGPA_CGPA_HEADERS + ["Back Paper Count"] + subject_fields
    
#     # ------------------- 1. Condensed Result (Main Sheet) -------------------
#     df_main_export = df_cleaned.drop(columns=['Detailed Subjects List'], errors='ignore')
#     ws_main.append(main_headers)
    
#     for index, row in df_main_export.iterrows():
#         row_list = [row.get(h, '') for h in main_headers]
#         ws_main.append(row_list)

#     # ------------------- 2. Subject-wise Failures Students -------------------
#     ws_failures.append(["Subject Code", "Subject Name", "Student Reg No", "Student Name", "Grade", "Type"])
#     for index, row in df_cleaned[df_cleaned['Back Paper Count'] > 0].iterrows():
#         for sub in row['Detailed Subjects List']:
#             if sub['Grade'].upper() == 'F':
#                 ws_failures.append([sub['Code'], sub['Name'], row['Reg No'], row['Name'], sub['Grade'], sub['Type']])

#     # ------------------- 3. Low Achievers Students (CGPA >= 5.0) -------------------
#     topper_df = df_cleaned[df_cleaned["CGPA"] >= 5.0].sort_values(by="CGPA", ascending=False)
#     ws_topper.append(["Reg No", "Name", "CGPA"])
#     for index, row in topper_df[['Reg No', 'Name', 'CGPA']].iterrows():
#         ws_topper.append(list(row))
        
#     # ------------------- 4. Fail Student Details Students (Back Count > 0) -------------------
#     fail_df = df_cleaned[df_cleaned['Back Paper Count'] > 0]
#     ws_failstudents.append(main_headers)
#     for index, row in fail_df.iterrows():
#         row_list = [row.get(h, '') for h in main_headers]
#         ws_failstudents.append(row_list)
#     ws_failstudents.append([])
#     ws_failstudents.append(["Total Failed/Back Students", len(fail_df)])

#     # ------------------- 5. All Backlog Summary -------------------
#     total_back = len(df_cleaned[df_cleaned['Back Paper Count'] > 0])
#     zero_back = len(df_cleaned[df_cleaned['Back Paper Count'] == 0])
    
#     back_counts = df_cleaned['Back Paper Count'].value_counts().reset_index()
#     back_counts.columns = ['Backlog Count', 'Number of Students']
    
#     ws_backlog.append(["Backlog Count", "Number of Students"])
#     ws_backlog.append(["Zero Backlog", zero_back])
#     for index, row in back_counts[back_counts['Backlog Count'] > 0].iterrows():
#         ws_backlog.append([row['Backlog Count'], row['Number of Students']])
    
#     # 6. SGPA Summary
#     sgpa_ranges = {">9.0": 0, "8.0-9.0": 0, "7.0-8.0": 0, "6.0-7.0": 0, "5.0-6.0": 0}
#     for cgpa in df_cleaned['CGPA'].dropna():
#         if cgpa > 9.0: sgpa_ranges[">9.0"] += 1
#         elif 8.0 <= cgpa <= 9.0: sgpa_ranges["8.0-9.0"] += 1
#         elif 7.0 <= cgpa < 8.0: sgpa_ranges["7.0-8.0"] += 1
#         elif 6.0 <= cgpa < 7.0: sgpa_ranges["6.0-7.0"] += 1
#         elif 5.0 <= cgpa < 6.0: sgpa_ranges["5.0-6.0"] += 1
    
#     ws_sgpa_summary.append(["SGPA Range", "Student Count"])
#     for k, v in sgpa_ranges.items():
#         ws_sgpa_summary.append([k, v])
        
#     # Final Save
#     wb.save(output_file)
#     st.success("Detailed multi-sheet Excel report created successfully!")


# import requests
# from bs4 import BeautifulSoup
# from concurrent.futures import ThreadPoolExecutor
# import streamlit as st
# import pandas as pd
# import time
# from typing import Optional, Dict, Any, List

# # --- Imports for Multi-Sheet Excel (Cloud-Friendly) ---
# import openpyxl
# from openpyxl.utils.dataframe import dataframe_to_rows
# # -----------------------------------------------------

# # --- Constants for Semester Data ---
# SGPA_CGPA_HEADERS = [
#     "SGPA Sem I", "SGPA Sem II", "SGPA Sem III", "SGPA Sem IV",
#     "SGPA Sem V", "SGPA Sem VI", "SGPA Sem VII", "SGPA Sem VIII",
#     "Final CGPA"
# ]


# # --- Core Scraper Logic (Requests/BS4) ---
# def fetch_and_parse_result(base_url, registration_no, retries=1, backoff_factor=1):
#     """Fetches result for a single registration number, extracts ALL details including subject marks and all semester SGPAs/CGPAs."""
#     url = f"{base_url}{registration_no}" 
#     headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
#     for attempt in range(retries):
#         try:
#             response = requests.get(url, headers=headers, timeout=10)
#             response.raise_for_status()
#             soup = BeautifulSoup(response.text, "html.parser")
            
#             # 1. Check for success marker
#             if not soup.select_one("#ContentPlaceHolder1_DataList1_RegistrationNoLabel_0"):
#                  return None

#             result = {
#                 "Reg No": soup.select_one("#ContentPlaceHolder1_DataList1_RegistrationNoLabel_0").text.strip(),
#                 "Name": soup.select_one("#ContentPlaceHolder1_DataList1_StudentNameLabel_0").text.strip(),
#                 "Father": soup.select_one("#ContentPlaceHolder1_DataList1_FatherNameLabel_0").text.strip(),
#                 "Mother": soup.select_one("#ContentPlaceHolder1_DataList1_MotherNameLabel_0").text.strip(),
#                 "College": soup.select_one("#ContentPlaceHolder1_DataList1_CollegeNameLabel_0").text.strip(),
#                 "Course": soup.select_one("#ContentPlaceHolder1_DataList1_CourseLabel_0").text.strip(),
#                 "Back Paper Count": 0,
#                 "Detailed Subjects List": [] 
#             }
            
#             # --- 2. Extract All Semester SGPAs/CGPA (GridView3) ---
#             sgpa_table = soup.select_one("#ContentPlaceHolder1_GridView3")
            
#             for header in SGPA_CGPA_HEADERS: result[header] = 'NA'
#             result["CGPA"] = 'NA'

#             if sgpa_table:
#                 sgpa_values = sgpa_table.find_all("tr")[-1].find_all("td")
                
#                 if len(sgpa_values) >= 9:
#                     for i, header in enumerate(SGPA_CGPA_HEADERS):
#                          result[header] = sgpa_values[i].text.strip()
                    
#                     # Fix: Ensure CGPA is the final result for sorting
#                     result["CGPA"] = result["Final CGPA"] if result["Final CGPA"] != 'NA' else result[SGPA_CGPA_HEADERS[-2]]
            
            
#             # --- 3. Detailed Subject Tables Scraping (Including IA/ESE) ---
            
#             def extract_subjects_from_table(table_id, subject_type):
#                 subjects = []
#                 table = soup.select_one(f"#{table_id}")
#                 if table:
#                     rows = table.find_all("tr")[1:] 
#                     for row in rows:
#                         cols = row.find_all("td")
#                         if len(cols) >= 8:
#                             subjects.append({
#                                 "Code": cols[0].text.strip(),
#                                 "Name": cols[1].text.strip(),
#                                 "Type": subject_type,
#                                 "IA": cols[3].text.strip(), 
#                                 "ESE": cols[2].text.strip(),
#                                 "Total": cols[4].text.strip(),
#                                 "Grade": cols[5].text.strip(),
#                                 "Credit": cols[6].text.strip()
#                             })
#                 return subjects

#             all_subjects = extract_subjects_from_table("ContentPlaceHolder1_GridView1", "Theory") 
#             all_subjects += extract_subjects_from_table("ContentPlaceHolder1_GridView2", "Practical")
            
#             back_count = 0
            
#             # Flatten detailed subjects for the main DataFrame/Excel output
#             for i, sub in enumerate(all_subjects):
#                 result["Detailed Subjects List"].append(sub)
                
#                 # Add columns to main result for display
#                 for key in ["Code", "Name", "Type", "IA", "ESE", "Total", "Grade", "Credit"]:
#                     result[f"Sub{i+1} {key}"] = sub[key]
                
#                 if sub["Grade"].upper() == "F" or sub["Grade"].upper() == "NE": # Include NE (Not Eligible) as a fail case
#                     back_count += 1

#             result["Back Paper Count"] = back_count
            
#             # Fill remaining columns up to 15 subjects 
#             for i in range(len(all_subjects), 15):
#                 for key in ["Code", "Name", "Type", "IA", "ESE", "Total", "Grade", "Credit"]:
#                     result[f"Sub{i+1} {key}"] = ""
            
#             return result
        
#         except (requests.exceptions.RequestException, AttributeError, ValueError) as e:
#             if attempt < retries - 1:
#                 time.sleep(backoff_factor * (2 ** attempt))
#             return None


# def fetch_all_results(base_url, start_reg, end_reg):
#     results = []
#     reg_numbers = list(range(start_reg, end_reg + 1))
#     MAX_WORKERS = min(10, len(reg_numbers)) 
    
#     progress_bar = st.progress(0)
    
#     with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
#         futures = {executor.submit(fetch_and_parse_result, base_url, reg_no): reg_no for reg_no in reg_numbers}
        
#         for i, future in enumerate(futures):
#             result = future.result()
#             if result:
#                 results.append(result)
            
#             progress_bar.progress((i + 1) / len(reg_numbers))
            
#     progress_bar.empty()
#     return results


# # --- Sorting Logic (No changes) ---
# def sort_by_current_cgpa(df):
#     df["CGPA"] = pd.to_numeric(df["CGPA"], errors="coerce")
#     return df.sort_values(by="CGPA", ascending=False, na_position='last')

# def sort_by_latest_semester_grade(df):
#     df_sorted = df.copy()
    
#     for header in reversed(SGPA_CGPA_HEADERS[:-1]): 
#         df_sorted[header] = pd.to_numeric(df_sorted[header], errors='coerce')
        
#     latest_sgpa_column = None
#     for header in reversed(SGPA_CGPA_HEADERS[:-1]):
#         if not df_sorted[header].isna().all():
#             latest_sgpa_column = header
#             break
            
#     if latest_sgpa_column:
#         return df_sorted.sort_values(by=latest_sgpa_column, ascending=False, na_position='last')
#     else:
#         return sort_by_current_cgpa(df)


# # --- Multi-Sheet Excel Export Function (No changes) ---
# def export_multi_sheet_excel(df: pd.DataFrame, output_file: str):
#     """
#     Creates the multi-sheet Excel report with detailed breakdown matching your requirements.
#     """
#     st.info("Generating detailed multi-sheet Excel report (XLSX)...")
    
#     wb = openpyxl.Workbook()
#     df_cleaned = df.copy()
#     df_cleaned["CGPA"] = pd.to_numeric(df_cleaned["CGPA"], errors="coerce")

#     # --- Sheet Creation ---
#     ws_main = wb.active
#     ws_main.title = "Condensed Result"
#     ws_failures = wb.create_sheet("Subject-wise Failures Students")
#     ws_topper = wb.create_sheet("Low Achievers Students") 
#     ws_failstudents = wb.create_sheet("Fail Student Details Students")
#     ws_backlog = wb.create_sheet("All Backlog Summary")
#     ws_sgpa_summary = wb.create_sheet("SGPA Summary")
    
#     # --- Headers for Main and Fail Details Sheets ---
#     subject_fields = []
#     for i in range(1, 16):
#         subject_fields += [f"Sub{i} Code", f"Sub{i} Name", f"Sub{i} Type", f"Sub{i} IA", f"Sub{i} ESE", f"Sub{i} Total", f"Sub{i} Grade", f"Sub{i} Credit"]

#     main_headers = ["Reg No", "Name", "Father", "Mother", "College", "Course"] + SGPA_CGPA_HEADERS + ["Back Paper Count"] + subject_fields
    
#     # ------------------- 1. Condensed Result (Main Sheet) -------------------
#     df_main_export = df_cleaned.drop(columns=['Detailed Subjects List'], errors='ignore')
#     ws_main.append(main_headers)
    
#     for index, row in df_main_export.iterrows():
#         row_list = [row.get(h, '') for h in main_headers]
#         ws_main.append(row_list)

#     # ------------------- 2. Subject-wise Failures Students -------------------
#     ws_failures.append(["Subject Code", "Subject Name", "Student Reg No", "Student Name", "Grade", "Type"])
#     for index, row in df_cleaned[df_cleaned['Back Paper Count'] > 0].iterrows():
#         for sub in row['Detailed Subjects List']:
#             if sub['Grade'].upper() == 'F' or sub['Grade'].upper() == 'NE':
#                 ws_failures.append([sub['Code'], sub['Name'], row['Reg No'], row['Name'], sub['Grade'], sub['Type']])

#     # ------------------- 3. Low Achievers Students (CGPA >= 5.0) -------------------
#     topper_df = df_cleaned[df_cleaned["CGPA"] >= 5.0].sort_values(by="CGPA", ascending=False)
#     ws_topper.append(["Reg No", "Name", "CGPA"])
#     for index, row in topper_df[['Reg No', 'Name', 'CGPA']].iterrows():
#         ws_topper.append(list(row))
        
#     # ------------------- 4. Fail Student Details Students (Back Count > 0) -------------------
#     fail_df = df_cleaned[df_cleaned['Back Paper Count'] > 0]
#     ws_failstudents.append(main_headers)
#     for index, row in fail_df.iterrows():
#         row_list = [row.get(h, '') for h in main_headers]
#         ws_failstudents.append(row_list)
#     ws_failstudents.append([])
#     ws_failstudents.append(["Total Failed/Back Students", len(fail_df)])

#     # ------------------- 5. All Backlog Summary -------------------
#     total_back = len(df_cleaned[df_cleaned['Back Paper Count'] > 0])
#     zero_back = len(df_cleaned[df_cleaned['Back Paper Count'] == 0])
    
#     back_counts = df_cleaned['Back Paper Count'].value_counts().reset_index()
#     back_counts.columns = ['Backlog Count', 'Number of Students']
    
#     ws_backlog.append(["Backlog Count", "Number of Students"])
#     ws_backlog.append(["Zero Backlog", zero_back])
#     for index, row in back_counts[back_counts['Backlog Count'] > 0].iterrows():
#         ws_backlog.append([row['Backlog Count'], row['Number of Students']])
    
#     # 6. SGPA Summary
#     sgpa_ranges = {">9.0": 0, "8.0-9.0": 0, "7.0-8.0": 0, "6.0-7.0": 0, "5.0-6.0": 0}
#     for cgpa in df_cleaned['CGPA'].dropna():
#         if cgpa > 9.0: sgpa_ranges[">9.0"] += 1
#         elif 8.0 <= cgpa <= 9.0: sgpa_ranges["8.0-9.0"] += 1
#         elif 7.0 <= cgpa < 8.0: sgpa_ranges["7.0-8.0"] += 1
#         elif 6.0 <= cgpa < 7.0: sgpa_ranges["6.0-7.0"] += 1
#         elif 5.0 <= cgpa < 6.0: sgpa_ranges["5.0-6.0"] += 1
    
#     ws_sgpa_summary.append(["SGPA Range", "Student Count"])
#     for k, v in sgpa_ranges.items():
#         ws_sgpa_summary.append([k, v])
        
#     # Final Save
#     wb.save(output_file)
#     st.success("Detailed multi-sheet Excel report created successfully!")


import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import streamlit as st
import pandas as pd
import time
from typing import Optional, Dict, Any, List

# --- Imports for Multi-Sheet Excel ---
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
# -------------------------------------

# --- Constants for Semester Data (Must be the same as url_config.py) ---
SGPA_CGPA_HEADERS = [
    "SGPA Sem I", "SGPA Sem II", "SGPA Sem III", "SGPA Sem IV",
    "SGPA Sem V", "SGPA Sem VI", "SGPA Sem VII", "SGPA Sem VIII",
    "Final CGPA"
]


# --- Core Scraper Logic (Requests/BS4) ---
def fetch_and_parse_result(base_url, registration_no, retries=1, backoff_factor=1):
    """Fetches result for a single registration number, extracts ALL details including subject marks and all semester SGPAs/CGPAs."""
    url = f"{base_url}{registration_no}" 
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 1. Check for success marker
            if not soup.select_one("#ContentPlaceHolder1_DataList1_RegistrationNoLabel_0"):
                 return None

            result = {
                "Reg No": soup.select_one("#ContentPlaceHolder1_DataList1_RegistrationNoLabel_0").text.strip(),
                "Name": soup.select_one("#ContentPlaceHolder1_DataList1_StudentNameLabel_0").text.strip(),
                "Father": soup.select_one("#ContentPlaceHolder1_DataList1_FatherNameLabel_0").text.strip(),
                "Mother": soup.select_one("#ContentPlaceHolder1_DataList1_MotherNameLabel_0").text.strip(),
                "College": soup.select_one("#ContentPlaceHolder1_DataList1_CollegeNameLabel_0").text.strip(),
                "Course": soup.select_one("#ContentPlaceHolder1_DataList1_CourseLabel_0").text.strip(),
                "Back Paper Count": 0,
                "Detailed Subjects List": [] 
            }
            
            # --- 2. Extract All Semester SGPAs/CGPA (GridView3) ---
            sgpa_table = soup.select_one("#ContentPlaceHolder1_GridView3")
            
            for header in SGPA_CGPA_HEADERS: result[header] = 'NA'
            result["CGPA"] = 'NA'

            if sgpa_table:
                sgpa_values = sgpa_table.find_all("tr")[-1].find_all("td")
                
                if len(sgpa_values) >= 9:
                    for i, header in enumerate(SGPA_CGPA_HEADERS):
                         result[header] = sgpa_values[i].text.strip()
                    
                    result["CGPA"] = result["Final CGPA"]
            
            
            # --- 3. Detailed Subject Tables Scraping (Including IA/ESE) ---
            
            def extract_subjects_from_table(table_id, subject_type):
                subjects = []
                table = soup.select_one(f"#{table_id}")
                if table:
                    rows = table.find_all("tr")[1:] 
                    for row in rows:
                        cols = row.find_all("td")
                        if len(cols) >= 8:
                            subjects.append({
                                "Code": cols[0].text.strip(),
                                "Name": cols[1].text.strip(),
                                "Type": subject_type,
                                "IA": cols[3].text.strip(), 
                                "ESE": cols[2].text.strip(),
                                "Total": cols[4].text.strip(),
                                "Grade": cols[5].text.strip(),
                                "Credit": cols[6].text.strip()
                            })
                return subjects

            all_subjects = extract_subjects_from_table("ContentPlaceHolder1_GridView1", "Theory") 
            all_subjects += extract_subjects_from_table("ContentPlaceHolder1_GridView2", "Practical")
            
            back_count = 0
            
            # Flatten detailed subjects for the main DataFrame/Excel output
            for i, sub in enumerate(all_subjects):
                result["Detailed Subjects List"].append(sub)
                
                # Add columns to main result for display
                for key in ["Code", "Name", "Type", "IA", "ESE", "Total", "Grade", "Credit"]:
                    result[f"Sub{i+1} {key}"] = sub[key]
                
                if sub["Grade"].upper() == "F":
                    back_count += 1

            result["Back Paper Count"] = back_count
            
            # Fill remaining columns up to 15 subjects 
            for i in range(len(all_subjects), 15):
                for key in ["Code", "Name", "Type", "IA", "ESE", "Total", "Grade", "Credit"]:
                    result[f"Sub{i+1} {key}"] = ""
            
            return result
        
        except (requests.exceptions.RequestException, AttributeError, ValueError) as e:
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


# --- Sorting Logic ---
def sort_by_current_cgpa(df):
    df["CGPA"] = pd.to_numeric(df["CGPA"], errors="coerce")
    return df.sort_values(by="CGPA", ascending=False, na_position='last')

def sort_by_latest_semester_grade(df):
    df_sorted = df.copy()
    
    for header in reversed(SGPA_CGPA_HEADERS[:-1]): 
        df_sorted[header] = pd.to_numeric(df_sorted[header], errors='coerce')
        
    latest_sgpa_column = None
    for header in reversed(SGPA_CGPA_HEADERS[:-1]):
        if not df_sorted[header].isna().all():
            latest_sgpa_column = header
            break
            
    if latest_sgpa_column:
        return df_sorted.sort_values(by=latest_sgpa_column, ascending=False, na_position='last')
    else:
        return sort_by_current_cgpa(df)


# --- Multi-Sheet Excel Export Function ---
def export_multi_sheet_excel(df: pd.DataFrame, output_file: str):
    """
    Creates the multi-sheet Excel report with detailed breakdown matching your requirements.
    """
    st.info("Generating detailed multi-sheet Excel report (XLSX)...")
    
    wb = openpyxl.Workbook()
    df_cleaned = df.copy()
    df_cleaned["CGPA"] = pd.to_numeric(df_cleaned["CGPA"], errors="coerce")

    # --- Sheet Creation ---
    ws_main = wb.active
    ws_main.title = "Condensed Result"
    ws_failures = wb.create_sheet("Subject-wise Failures Students")
    ws_topper = wb.create_sheet("Low Achievers Students") 
    ws_failstudents = wb.create_sheet("Fail Student Details Students")
    ws_backlog = wb.create_sheet("All Backlog Summary")
    ws_sgpa_summary = wb.create_sheet("SGPA Summary")
    
    # --- Headers for Main and Fail Details Sheets ---
    subject_fields = []
    for i in range(1, 16):
        subject_fields += [f"Sub{i} Code", f"Sub{i} Name", f"Sub{i} Type", f"Sub{i} IA", f"Sub{i} ESE", f"Sub{i} Total", f"Sub{i} Grade", f"Sub{i} Credit"]

    main_headers = ["Reg No", "Name", "Father", "Mother", "College", "Course"] + SGPA_CGPA_HEADERS + ["Back Paper Count"] + subject_fields
    
    # ------------------- 1. Condensed Result (Main Sheet) -------------------
    df_main_export = df_cleaned.drop(columns=['Detailed Subjects List'], errors='ignore')
    ws_main.append(main_headers)
    
    for index, row in df_main_export.iterrows():
        row_list = [row.get(h, '') for h in main_headers]
        ws_main.append(row_list)

    # ------------------- 2. Subject-wise Failures Students -------------------
    ws_failures.append(["Subject Code", "Subject Name", "Student Reg No", "Student Name", "Grade", "Type"])
    for index, row in df_cleaned[df_cleaned['Back Paper Count'] > 0].iterrows():
        for sub in row['Detailed Subjects List']:
            if sub['Grade'].upper() == 'F':
                ws_failures.append([sub['Code'], sub['Name'], row['Reg No'], row['Name'], sub['Grade'], sub['Type']])

    # ------------------- 3. Low Achievers Students (CGPA >= 5.0) -------------------
    topper_df = df_cleaned[df_cleaned["CGPA"] >= 5.0].sort_values(by="CGPA", ascending=False)
    ws_topper.append(["Reg No", "Name", "CGPA"])
    for index, row in topper_df[['Reg No', 'Name', 'CGPA']].iterrows():
        ws_topper.append(list(row))
        
    # ------------------- 4. Fail Student Details Students (Back Count > 0) -------------------
    fail_df = df_cleaned[df_cleaned['Back Paper Count'] > 0]
    ws_failstudents.append(main_headers)
    for index, row in fail_df.iterrows():
        row_list = [row.get(h, '') for h in main_headers]
        ws_failstudents.append(row_list)
    ws_failstudents.append([])
    ws_failstudents.append(["Total Failed/Back Students", len(fail_df)])

    # ------------------- 5. All Backlog Summary -------------------
    total_back = len(df_cleaned[df_cleaned['Back Paper Count'] > 0])
    zero_back = len(df_cleaned[df_cleaned['Back Paper Count'] == 0])
    
    back_counts = df_cleaned['Back Paper Count'].value_counts().reset_index()
    back_counts.columns = ['Backlog Count', 'Number of Students']
    
    ws_backlog.append(["Backlog Count", "Number of Students"])
    ws_backlog.append(["Zero Backlog", zero_back])
    for index, row in back_counts[back_counts['Backlog Count'] > 0].iterrows():
        ws_backlog.append([row['Backlog Count'], row['Number of Students']])
    
    # 6. SGPA Summary
    sgpa_ranges = {">9.0": 0, "8.0-9.0": 0, "7.0-8.0": 0, "6.0-7.0": 0, "5.0-6.0": 0}
    for cgpa in df_cleaned['CGPA'].dropna():
        if cgpa > 9.0: sgpa_ranges[">9.0"] += 1
        elif 8.0 <= cgpa <= 9.0: sgpa_ranges["8.0-9.0"] += 1
        elif 7.0 <= cgpa < 8.0: sgpa_ranges["7.0-8.0"] += 1
        elif 6.0 <= cgpa < 7.0: sgpa_ranges["6.0-7.0"] += 1
        elif 5.0 <= cgpa < 6.0: sgpa_ranges["5.0-6.0"] += 1
    
    ws_sgpa_summary.append(["SGPA Range", "Student Count"])
    for k, v in sgpa_ranges.items():
        ws_sgpa_summary.append([k, v])
        
    # Final Save
    wb.save(output_file)
    st.success("Detailed multi-sheet Excel report created successfully!")