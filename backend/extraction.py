import pypdf

def extract_text(pdf_file):
    full_text = ""
    try:
        reader = pypdf.PdfReader(pdf_file)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                full_text = full_text + t + "\n"
    except Exception as e:
        print("Error reading PDF:", e)
        return ""
    return full_text