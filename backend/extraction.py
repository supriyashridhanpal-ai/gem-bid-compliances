
from pathlib import Path
from PyPDF2 import PdfReader


def extract_text(pdf_path):
    """Extract readable text from a PDF document."""

    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError("PDF file not found.")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    try:
        reader = PdfReader(str(path))

        if reader.is_encrypted:
            raise ValueError("The PDF is password-protected.")

        extracted_text = []

        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text.append(text)

        return "\n".join(extracted_text).strip()

    except ValueError:
        raise
    except Exception as error:
        raise ValueError(
            f"Unable to read PDF: {error}"
        ) from error
