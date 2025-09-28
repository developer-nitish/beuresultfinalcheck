

# --- Constants for Semester Data ---
SGPA_CGPA_HEADERS = [
    "SGPA Sem I", "SGPA Sem II", "SGPA Sem III", "SGPA Sem IV",
    "SGPA Sem V", "SGPA Sem VI", "SGPA Sem VII", "SGPA Sem VIII",
    "Final CGPA"
]

def get_ordinal_suffix(n):
    """Returns the correct English ordinal suffix for a number (1st, 2nd, 3rd, 4th, etc.)"""
    if 10 <= n % 100 <= 20:
        return 'th'
    else:
        return {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')

def generate_url_templates():
    """Generates a base dictionary for all batches and semesters."""
    URL_TEMPLATES = {}
    
    for start_year in range(2019, 2031):
        batch_label = f"{start_year}-{start_year + 4} Batch"
        URL_TEMPLATES[batch_label] = {}
        
        for sem_num in range(1, 9):
            sem_roman = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII', 8: 'VIII'}[sem_num]
            
            # Use 'Manual' as a placeholder for the exam year in the structure
            URL_TEMPLATES[batch_label][f"Sem {sem_roman}"] = {
                "base": "https://results.beup.ac.in/ResultsBTech",
                "sem_num": sem_num,
                "batch_year": start_year
            }
    return URL_TEMPLATES

ALL_URL_TEMPLATES = generate_url_templates()

def build_final_api_url(template_data, exam_year):
    """Constructs the final API URL using the manual exam_year input and correct ordinal suffix."""
    sem_num = template_data['sem_num']
    start_year = template_data['batch_year']
    sem_roman = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII', 8: 'VIII'}[sem_num]
    
    # Get the correct suffix (st, nd, rd, th)
    suffix = get_ordinal_suffix(sem_num)
    
    # Construct the dynamic file name part (e.g., BTech1stSem2024_B2024Pub)
    sem_part = f"BTech{sem_num}{suffix}Sem{exam_year}_B{start_year}Pub"
    
    # Special case for Sem I 2023 batch (B2023)
    if start_year == 2023 and sem_num == 1:
        return f"https://results.beup.ac.in/BTech1stSem2024_Old_B2023Results.aspx?RegNo="

    # Standard API construction using the correct suffix
    return f"https://results.beup.ac.in/Results{sem_part}.aspx?Sem={sem_roman}&RegNo="