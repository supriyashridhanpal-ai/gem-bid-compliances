
import re


def normalize_text(text):
    """Normalize document text for keyword matching."""
    return re.sub(r"\s+", " ", str(text).lower()).strip()


def check_compliance(extracted_text, requirements):
    """Compare tender requirements with extracted PDF text."""

    if isinstance(requirements, str):
        requirements = re.split(r"[,;\n]+", requirements)

    requirements = [
        str(item).strip()
        for item in (requirements or [])
        if str(item).strip()
    ]

    if not extracted_text or not str(extracted_text).strip():
        return {
            "status": "MANUAL_REVIEW",
            "score": 0.0,
            "matched_requirements": [],
            "missing_requirements": [],
            "manual_review": requirements,
            "message": "No readable document text is available.",
        }

    if not requirements:
        return {
            "status": "MANUAL_REVIEW",
            "score": 0.0,
            "matched_requirements": [],
            "missing_requirements": [],
            "manual_review": [],
            "message": "No tender requirements were provided.",
        }

    document_text = normalize_text(extracted_text)
    matched = []
    missing = []
    manual_review = []

    for requirement in requirements:
        normalized_requirement = normalize_text(requirement)

        if normalized_requirement.startswith("verify:"):
            item = requirement.split(":", 1)[1].strip()
            if item:
                manual_review.append(item)
        elif normalized_requirement in document_text:
            matched.append(requirement)
        else:
            missing.append(requirement)

    total = len(matched) + len(missing) + len(manual_review)
    score = round(len(matched) / total * 100, 2) if total else 0.0

    if manual_review:
        status = "MANUAL_REVIEW"
        message = "Human review is required before confirming compliance."
    elif missing:
        status = "NON_COMPLIANT"
        message = "Some requirements were not found in the document."
    else:
        status = "VERIFIED"
        message = "All listed requirements were found in the document."

    return {
        "status": status,
        "score": score,
        "matched_requirements": matched,
        "missing_requirements": missing,
        "manual_review": manual_review,
        "message": message,
    }
