from pathlib import Path
from pypdf import PdfReader


def extract_text(pdf_path):
    """
    Extract text from a PDF document.

    Parameter:
        pdf_path: Path of the uploaded PDF.

    Returns:
        Extracted text as a string.
    """

    file_path = Path(pdf_path)

    # Step 1: Check whether the file exists
    if not file_path.is_file():
        raise FileNotFoundError(
            f"PDF file not found: {file_path}"
        )

    # Step 2: Check the file extension
    if file_path.suffix.lower() != ".pdf":
        raise ValueError(
            "Please provide a PDF file."
        )

    # Step 3: Open the PDF
    reader = PdfReader(str(file_path))

    # Step 4: Check whether the PDF is encrypted
    if reader.is_encrypted:
        raise ValueError(
            "Encrypted PDFs are not supported."
        )

    # Step 5: Extract text from every page
    extracted_pages = []

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            extracted_pages.append(page_text)

    # Step 6: Combine the page text
    extracted_text = "\n".join(extracted_pages).strip()

    # Step 7: Check whether text was extracted
    if not extracted_text:
        raise ValueError(
            "No readable text found in the PDF. "
            "The document may be scanned and require OCR."
        )

    return extracted_text


# Run this section only when testing this file directly
if __name__ == "__main__":
    print("PDF Text Extraction Module")
    print("Import extract_text() into app.py to process uploads.")