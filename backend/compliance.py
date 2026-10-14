
import re


def normalize_text(text):
    """Convert text to lowercase and remove extra spaces."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def check_compliance(extracted_text, requirements):
    """
    Compare tender requirements with the extracted PDF text.
    """

    if not extracted_text or not extracted_text.strip():
        return {
            "status": "Manual Review",
            "score": 0,
            "matched_requirements": [],
            "missing_requirements": requirements,
            "manual_review": True,
            "message": "No readable text found. Manual review is required."
        }

    document_text = normalize_text(extracted_text)

    matched_requirements = []
    missing_requirements = []

    for requirement in requirements:
        requirement = requirement.strip()

        if not requirement:
            continue

        normalized_requirement = normalize_text(requirement)

        if normalized_requirement in document_text:
            matched_requirements.append(requirement)
        else:
            missing_requirements.append(requirement)

    total = len(matched_requirements) + len(missing_requirements)

    if total == 0:
        score = 0
        status = "Manual Review"
        manual_review = True
        message = "Enter at least one valid requirement."
    else:
        score = round(
            (len(matched_requirements) / total) * 100
        )

        if not missing_requirements:
            status = "Match"
            manual_review = False
            message = "All entered requirements were found."
        else:
            status = "Manual Review"
            manual_review = True
            message = "Some requirements were not found in the document."

    return {
        "status": status,
        "score": score,
        "matched_requirements": matched_requirements,
        "missing_requirements": missing_requirements,
        "manual_review": manual_review,
        "message": message
    }
