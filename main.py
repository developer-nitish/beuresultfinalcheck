import os
import time
import streamlit as st
import openpyxl
import requests
from bs4 import BeautifulSoup
import re

# ---------------------------
# Helper: Extract subjects from a table
# ---------------------------
def extract_subjects_from_html(soup, table_id, subject_type):
    """
    Parses the subject table from the result HTML using its ID.
    """
    subjects = []
    # Use CSS selector to find the table
    table = soup.select_one(f"#{table_id}")
    if table:
        # Skip the header row (tr) and iterate through subject rows
        rows = table.find_all("tr")[1:]
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 7:
                subjects.append({
                    "code": cols[0].text.strip(),
                    "name": cols[1].text.strip(),
                    "ese": cols[2].text.strip(),
                    "ia": cols[3].text.strip(),
                    "total": cols[4].text.strip(),
                    "grade": cols[5].text.strip(),
                    "credit": cols[6].text.strip(),
                    "type": subject_type
                })
    return subjects

# ---------------------------
# Helper: Fetch and Parse Result via Robust POST Request Simulation
# ---------------------------
def fetch_and_parse_result(base_url, registration_no, retries=3, backoff_factor=1):
    """
    Simulates a robust ASP.NET form submission to fetch the result.
    """
    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': base_url,
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    for attempt in range(retries):
        try:
            # 1. GET Request to fetch all form hidden fields
            get_response = session.get(base_url, headers=headers, timeout=15)
            get_response.raise_for_status()
            soup = BeautifulSoup(get_response.text, "html.parser")

            # Collect all hidden inputs in the form
            post_data = {}
            for tag in soup.find_all("input", type="hidden"):
                if tag.get('name'):
                    post_data[tag.get('name')] = tag.get('value', '')
            
            # Add the required fields for submission
            post_data.update({
                '__EVENTTARGET': '',
                '__EVENTARGUMENT': '',
                'ContentPlaceHolder1_TextBox_RegNo': str(registration_no),
                'ContentPlaceHolder1_Button_Show': 'Show Result' 
            })

            # 2. POST Request to submit the form
            post_response = session.post(base_url, data=post_data, headers=headers, timeout=15)
            post_response.raise_for_status()
            result_soup = BeautifulSoup(post_response.text, "html.parser")
            
            # Check for a specific element that only appears on a successful result page
            if not result_soup.select_one("#ContentPlaceHolder1_DataList1_StudentNameLabel_0"):
                # Result not found (e.g., wrong reg no or server error)
                return None 

            # 3. Parse successful result page
            
            # --- Basic Student Details ---
            result = {
                "reg": result_soup.select_one("#ContentPlaceHolder1_DataList1_RegistrationNoLabel_0").text.strip(),
                "name": result_soup.select_one("#ContentPlaceHolder1_DataList1_StudentNameLabel_0").text.strip(),
                "father": result_soup.select_one("#ContentPlaceHolder1_DataList1_FatherNameLabel_0").text.strip(),
                "mother": result_soup.select_one("#ContentPlaceHolder1_DataList1_MotherNameLabel_0").text.strip(),
                "college": result_soup.select_one("#ContentPlaceHolder1_DataList1_CollegeNameLabel_0").text.strip(),
                "course": result_soup.select_one("#ContentPlaceHolder1_DataList1_CourseLabel_0").text.strip(),
                "semester": result_soup.select_one("#ContentPlaceHolder1_DataList2_Exam_Name_0").text.strip(),
            }

            # --- SGPA/CGPA Table (ContentPlaceHolder1_GridView3) ---
            sgpas = []
            cgpa = ""
            sgpa_table = result_soup.select_one("#ContentPlaceHolder1_GridView3")
            if sgpa_table:
                rows = sgpa_table.find_all("tr")
                if len(rows) > 1:
                    cells = rows[1].find_all("td")
                    sgpas = [c.text.strip() for c in cells[:8]]
                    cgpa = cells[8].text.strip()
            result["sgpas"] = sgpas
            result["cgpa"] = cgpa

            # --- Remark & publish date ---
            try:
                result["remark"] = result_soup.select_one("#ContentPlaceHolder1_DataList3_remarkLabel_0").text.strip()
            except:
                result["remark"] = ""
            
            try:
                pub_date_match = re.search(r'Date of Publication of Result\s*:\s*([\d\-\/]+)', post_response.text)
                result["pub_date"] = pub_date_match.group(1).strip() if pub_date_match else ""
            except:
                result["pub_date"] = ""

            # --- Subjects (theory + practical) ---
            result["subjects"] = []
            result["subjects"].extend(extract_subjects_from_html(result_soup, "ContentPlaceHolder1_GridView1", "Theory"))
            result["subjects"].extend(extract_subjects_from_html(result_soup, "ContentPlaceHolder1_GridView2", "Practical"))
            
            return result
        
        except requests.exceptions.RequestException as e:
            st.warning(f"Attempt {attempt + 1} failed for {registration_no} due to connection error: {e}")
            if attempt < retries - 1:
                time.sleep(backoff_factor * (2 ** attempt))
            else:
                return None
        except Exception as e:
            st.error(f"Error parsing result for {registration_no}: {e}")
            return None


# ---------------------------
# Main Scraper
# ---------------------------
def run_scraper(start_reg, end_reg, url):
    if not url.endswith('.aspx'):
        st.error("❌ कृपया सही और पूरा BEU Result URL डालें। यह .aspx पर समाप्त होना चाहिए।")
        return

    wb = openpyxl.Workbook()
    ws_main = wb.active
    ws_main.title = "Condensed Result"
    ws_failures = wb.create_sheet("Subject-wise Failures Students")
    ws_topper = wb.create_sheet("Low Achievers Students") 
    ws_failstudents = wb.create_sheet("Fail Student Details Students")
    ws_backlog = wb.create_sheet("All Backlog Summary")
    ws_sgpa_summary = wb.create_sheet("SGPA Summary")

    # Headers for Main Sheet
    headers = ["Reg No", "Name", "Father", "Mother", "College", "Course", "Semester"]
    for i in range(1, 16):
        headers += [f"Sub{i} Code", f"Sub{i} Name", f"Sub{i} Type", "IA", "ESE", "Total", "Grade", "Credit"]
    headers += ["SGPA Sem I", "Sem II", "Sem III", "Sem IV", "Sem V", "Sem VI", "Sem VII", "Sem VIII", "CGPA", "Remarks", "Publish Date"]

    ws_main.append(headers)
    ws_failures.append(["Subject Code", "Subject Name", "Student Reg No", "Student Name", "Semester", "Grade", "Type"])
    ws_topper.append(["Reg No", "Name", "CGPA"])
    ws_failstudents.append(headers)
    ws_sgpa_summary.append(["SGPA Range", "Student Count"])

    fail_count = 0
    backlog_counter = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, '5+': 0}
    sgpa_ranges = {">9.0": 0, "8.0-9.0": 0, "7.0-8.0": 0, "6.0-7.0": 0, "5.0-6.0": 0} 

    # Progress bar for Streamlit
    total_regs = end_reg - start_reg + 1
    progress_bar = st.progress(0, text=f"Scraping 0 of {total_regs} students...")
    student_counter = 0

    for reg in range(start_reg, end_reg + 1):
        st.write(f"🔍 Checking: {reg}")
        data = fetch_and_parse_result(url, reg)
        
        student_counter += 1
        progress_bar.progress(student_counter / total_regs, text=f"Scraping {student_counter} of {total_regs} students... (Current: {reg})")

        if not data:
            st.warning(f"⚠️ Result Not Found for {reg}")
            continue

        row = [data["reg"], data["name"], data["father"], data["mother"], data["college"], data["course"], data["semester"]]
        fail_count_student = 0

        # Add subjects
        for sub in data["subjects"]:
            row += [sub["code"], sub["name"], sub["type"], sub["ia"], sub["ese"], sub["total"], sub["grade"], sub["credit"]]
            if sub["grade"].upper() == "F":
                fail_count_student += 1
                ws_failures.append([sub["code"], sub["name"], data["reg"], data["name"], data["semester"], sub["grade"], sub["type"]])

        # Pad with empty cells if fewer than 15 subjects
        while len(data["subjects"]) < 15:
            row += ["", "", "", "", "", "", "", ""]
            data["subjects"].append(None)

        # SGPA + CGPA
        sgpas = data["sgpas"]
        sgpas = sgpas + ["NA"] * (8 - len(sgpas)) 
        row += sgpas + [data["cgpa"], data["remark"], data["pub_date"]]
        ws_main.append(row)

        # Update Fail Students sheet
        if fail_count_student > 0:
            ws_failstudents.append(row)
            fail_count += 1

        # Update Low Achievers/Topper sheet
        try:
            if float(data["cgpa"]) >= 5.0:
                ws_topper.append([data["reg"], data["name"], data["cgpa"]])
        except:
            pass

        # Update Backlog counter
        if fail_count_student in backlog_counter:
            backlog_counter[fail_count_student] += 1
        else:
            backlog_counter['5+'] += 1

        # Update SGPA ranges (using 4th sem as per original logic, index 3)
        try:
            current_sgpa_str = sgpas[3]
            if current_sgpa_str != "NA" and current_sgpa_str:
                current_sgpa = float(current_sgpa_str)
                if current_sgpa > 9.0:
                    sgpa_ranges[">9.0"] += 1
                elif 8.0 <= current_sgpa <= 9.0:
                    sgpa_ranges["8.0-9.0"] += 1
                elif 7.0 <= current_sgpa < 8.0:
                    sgpa_ranges["7.0-8.0"] += 1
                elif 6.0 <= current_sgpa < 7.0:
                    sgpa_ranges["6.0-7.0"] += 1
                elif 5.0 <= current_sgpa < 6.0:
                    sgpa_ranges["5.0-6.0"] += 1
        except:
            pass
        
    progress_bar.empty()
    st.info("📊 Generating Summary Sheets...")

    # Final Summary updates
    ws_failstudents.append([])
    ws_failstudents.append(["Total Failed Students", fail_count])
    ws_backlog.append(["Backlog Count", "Number of Students"])
    for k in [0, 1, 2, 3, 4, '5+']:
        ws_backlog.append([f"{k} Backlogs" if k != 0 else "Zero Backlog", backlog_counter[k]])
    for k, v in sgpa_ranges.items():
        ws_sgpa_summary.append([k, v])

    # Save file
    base_name = "beu_result"
    filename = f"{base_name}_{int(time.time())}.xlsx" 

    try:
        wb.save(filename)
        st.success(f"✅ All done! Result saved as {filename}")
        with open(filename, "rb") as f:
            st.download_button("📥 Download Excel File", f, file_name=filename)
        os.remove(filename) # Clean up file after download
    except Exception as e:
        st.error(f"❌ Failed to save or download file: {e}")


# ---------------------------
# Streamlit UI
# ---------------------------
def main():
    st.set_page_config(page_title="BEU Result Scraper", layout="centered")
    st.markdown(
        """
        <div style="text-align:center; padding:15px; background-color:#003366; color:white; border-radius:10px;">
            <h2>Bihar Engineering University (BEU), Patna</h2>
            <h3>Automated Result Scraper Tool (Cloud Ready)</h3>
            <p>Fetch, Parse & Export Results to Excel/CSV – Fast & Reliable</p>
        </div>
        """, unsafe_allow_html=True)

    st.title(" 🤖 BEU Result Scraper Tool")
    
    # URL Input - User must provide the complete URL of the result page
    default_url = "https://results.beup.ac.in/BTech4thSem2024_B2022Results.aspx"
    url = st.text_input("🔗 Enter BEU Result URL (e.g., must end with .aspx)", default_url)
    
    # Registration Number Inputs - Corrected min_value
    default_start = 22157147001
    default_end = 22157147005
    
    # Corrected min_value to 12-digit minimum
    start_reg = st.number_input("Start Registration Number", min_value=100000000000, step=1, value=default_start, format="%d")
    end_reg = st.number_input("End Registration Number", min_value=100000000000, step=1, value=default_end, format="%d")

    st.warning("⚠️ कृपया एक बार में केवल एक कॉलेज के रोल नंबर ही डालें। बड़ी रेंज पर सर्वर से ब्लॉक होने का खतरा रहता है।")

    if st.button("🚀 Start Scraping"):
        if not url or not url.endswith('.aspx'):
            st.error("❌ कृपया एक मान्य BEU Result URL डालें जो `.aspx` पर समाप्त होता हो।")
        elif start_reg > end_reg:
            st.error("❌ Start Reg. No, End Reg. No से कम होना चाहिए।")
        else:
            run_scraper(int(start_reg), int(end_reg), url)

    # ===== FOOTER =====
    st.markdown(
        """
        <hr>
        <div style="text-align:center; font-size:14px; padding:10px;">
            <p>💻 Developed by <b>GEC Aurangabad</b></p>
            <p>
                 <a href="https://github.com/developer-nitish" target="_blank">GitHub</a>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()