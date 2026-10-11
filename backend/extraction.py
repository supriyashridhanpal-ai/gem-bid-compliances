import pypdf

def extract_text_from_pdf(pdf_file):
    full_text = ""
    try:
        reader = pypdf.PdfReader(pdf_file)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text = full_text + text + "\n"
    except Exception as error:
        print("Error reading PDF:", error)
        return ""
    return full_text