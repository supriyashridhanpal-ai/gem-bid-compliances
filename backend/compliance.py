import re


def normalize_text(text):
    """Convert text to lowercase and normalize whitespace."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def check_compliance(extracted_text, requirements):
    """
    Compare extracted bid document text with tender requirements.

    Args:
        extracted_text (str): Text extracted from the uploaded PDF.
        requirements (list): Required items, such as ["GST", "PAN"].

    Returns:
        dict: Compliance status, score, matched items,
              missing items, and items requiring manual review.
    """

    if not isinstance(extracted_text, str) or not extracted_text.strip():
        return {
            "status": "MANUAL_REVIEW",
            "score": 0.0,
            "matched_requirements": [],
            "missing_requirements": [],
            "manual_review": list(requirements)
            if isinstance(requirements, list) else [],
            "message": "No readable document text is available."
        }

    if not isinstance(requirements, list) or not requirements:
        return {
            "status": "MANUAL_REVIEW",
            "score": 0.0,
            "matched_requirements": [],
            "missing_requirements": [],
            "manual_review": [],
            "message": "Please provide a list of tender requirements."
        }

    document_text = normalize_text(extracted_text)

    matched = []
    missing = []
    manual_review = []

    # Check each requirement separately
    for requirement in requirements:
        requirement_text = str(requirement).strip()

        if not requirement_text:
            continue

        normalized_requirement = normalize_text(requirement_text)

        # Values that need human or specialized validation
        if normalized_requirement.startswith("verify:"):
            manual_review.append(
                requirement_text.split(":", 1)[1].strip()
            )
            continue

        # Check whether the required phrase appears in the document
        if normalized_requirement in document_text:
            matched.append(requirement_text)
        else:
            missing.append(requirement_text)

    total = len(matched) + len(missing) + len(manual_review)

    score = round((len(matched) / total) * 100, 2) if total else 0.0

    # Determine the overall result
    if manual_review:
        status = "MANUAL_REVIEW"
    elif missing:
        status = "NON_COMPLIANT"
    else:
        status = "VERIFIED"

    return {
        "status": status,
        "score": score,
        "matched_requirements": matched,
        "missing_requirements": missing,
        "manual_review": manual_review,
        "message": (
            "All listed requirements were found in the document."
            if status == "VERIFIED"
            else
            "Some requirements are missing."
            if status == "NON_COMPLIANT"
            else
            "Human review is required before confirming compliance."
        )
    }


# Test the compliance module independently
if __name__ == "__main__":
    sample_text = """
    GeM Bid Compliance Test
    Company Name: ABC Technologies
    GST: 12345678901234
    PAN: ABCDE1234F
    """

    tender_requirements = ["GST", "PAN", "Turnover"]

    result = check_compliance(sample_text, tender_requirements)

    print("GeM Bid Compliance Results")
    print("--------------------------")
    print("Status:", result["status"])
    print("Compliance Score:", result["score"], "%")
    print("Matched:", result["matched_requirements"])
    print("Missing:", result["missing_requirements"])
    print("Manual Review:", result["manual_review"])
    print("Message:", result["message"])