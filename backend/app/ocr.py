import pytesseract
from PIL import Image
import re
import os
import cv2
import numpy as np

def preprocess_image(image_path: str):
    """Cleans and prepares an image for OCR to improve accuracy."""
    try:
        img = cv2.imread(image_path)
        if img is None: return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        denoised = cv2.medianBlur(binary, 3)
        return denoised
    except Exception as e:
        print(f"Error during image pre-processing: {e}")
        return None

def extract_text_from_image(image_path: str) -> str:
    """Extracts raw text from an image file after pre-processing it."""
    try:
        if not os.path.exists(image_path): return ""
        processed_image = preprocess_image(image_path)
        if processed_image is None:
            return pytesseract.image_to_string(Image.open(image_path))
        return pytesseract.image_to_string(processed_image)
    except Exception as e:
        print(f"Error during OCR processing: {e}")
        return ""

def clean_text(text: str) -> str:
    """A new, crucial helper function to remove non-alphanumeric noise from text."""
    # Allows letters, numbers, spaces, dots, and commas. Removes everything else.
    return re.sub(r'[^A-Za-z0-9\s.,]', '', text)

def parse_financial_document(text: str) -> dict:
    """
    More intelligently parses text to find salary by looking for keywords and cleaning the results.
    """
    data = {"salary": None, "pan": None}
    
    pan_match = re.search(r'[A-Z]{5}[0-9]{4}[A-Z]{1}', text)
    if pan_match: data["pan"] = pan_match.group(0)
        
    salary_keywords = ['net pay', 'net salary', 'gross salary', 'total earnings', 'net amount', 'take home']
    money_regex = r'([\d,]+\.?\d*)' # Finds numbers with commas
    
    lines = text.lower().split('\n')
    found_salary = None
    max_found_salary = 0

    for line in lines:
        for keyword in salary_keywords:
            if keyword in line:
                # Find all potential numbers on the line where a keyword was found
                potential_salaries = re.findall(money_regex, line)
                for s in potential_salaries:
                    try:
                        # Clean the number string by removing commas before converting to float
                        cleaned_s = s.replace(',', '')
                        salary_figure = float(cleaned_s)
                        # Take the largest plausible number found on the line as the salary
                        if 5000 < salary_figure < 500000 and salary_figure > max_found_salary:
                            max_found_salary = salary_figure
                    except (ValueError, IndexError):
                        continue
    
    if max_found_salary > 0:
        data["salary"] = max_found_salary
        
    return data

def parse_aadhaar_document(text: str) -> dict:
    """Parses text to find Aadhaar number and name using more robust heuristics."""
    data = {"name": None, "aadhaar_number": None}

    aadhaar_match = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', text)
    if aadhaar_match:
        data["aadhaar_number"] = aadhaar_match.group(0).replace(" ", "")

    lines = text.split('\n')
    for i, line in enumerate(lines):
        # Look for the line before 'Date of Birth' or 'DOB'
        if 'date of birth' in line.lower() or 'dob' in line.lower():
            if i > 0:
                # This is the new, more robust cleaning step.
                # It removes any garbage characters the OCR might have picked up.
                potential_name = re.sub(r'[^A-Za-z\s.]', '', lines[i-1]).strip()
                if len(potential_name.split()) > 1: # A real name usually has at least two parts
                    data["name"] = potential_name
                    break
    return data

