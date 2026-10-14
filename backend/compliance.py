
import re


def normalize_text(text):
    """Normalize text for case-insensitive matching."""
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def split_sentences(text):
    """Split document text into simple sentence-like sections."""
    return re.split(r"[.!?;\n]+", str(text))


def check_compliance(extracted_text, requirements):
    """
    Compare tender requirements with extracted PDF text.

    VERIFIED: All requirements were found.
    NON_COMPLIANT: One or more requirements are missing.
    MANUAL_REVIEW: Text or requirements are unavailable,
                   or a requirement explicitly needs human review.
    """

    if isinstance(requirements, str):
        requirements = re.split(r"[,;\n]+", requirements)

    if not isinstance(requirements, (list, tuple)):
        requirements = []

    requirements = [
        str(item).strip()
        for item in requirements
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
    sentences = [
        normalize_text(sentence)
        for sentence in split_sentences(extracted_text)
        if normalize_text(sentence)
    ]

    matched = []
    missing = []
    manual_review = []

    negative_phrases = (
        "omitted",
        "missing",
        "not provided",
        "unavailable",
        "not available",
        "not submitted",
        "not included",
        "not applicable",
    )

    for requirement in requirements:
        normalized_requirement = normalize_text(requirement)

        if normalized_requirement.startswith("verify:"):
            item = requirement.split(":", 1)[1].strip()
            if item:
                manual_review.append(item)
            continue

        # Look only at sentences that mention this requirement.
        relevant_sentences = [
            sentence
            for sentence in sentences
            if normalized_requirement in sentence
        ]

        if not relevant_sentences:
            missing.append(requirement)
            continue

        # If a relevant sentence explicitly says the requirement
        # is absent, do not count it as satisfied.
        explicitly_absent = any(
            any(phrase in sentence for phrase in negative_phrases)
            for sentence in relevant_sentences
        )

        if explicitly_absent:
            missing.append(requirement)
        else:
            matched.append(requirement)

    total = len(matched) + len(missing) + len(manual_review)
    score = round(len(matched) / total * 100, 2) if total else 0.0

    if manual_review:
        status = "MANUAL_REVIEW"
        message = "Human review is required before confirming compliance."
    elif missing:
        status = "NON_COMPLIANT"
        message = "Some requirements were not found or were explicitly absent."
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


if __name__ == "__main__":
    requirements = ["GST", "PAN", "Turnover"]

    test_cases = [
        (
            "TEST 1: All requirements present",
            """
            Company Name: ABC Technologies Pvt Ltd.
            GST: 33ABCDE1234F1Z5.
            PAN: ABCDE1234F.
            Turnover: 5000000 INR.
            """,
            "VERIFIED",
        ),
        (
            "TEST 2: Turnover explicitly omitted",
            """
            Company Name: ABC Technologies Pvt Ltd.
            GST: 33ABCDE1234F1Z5.
            PAN: ABCDE1234F.
            Turnover information is intentionally omitted.
            """,
            "NON_COMPLIANT",
        ),
        (
            "TEST 3: Human review required",
            """
            Company Name: ABC Technologies Pvt Ltd.
            GST: 33ABCDE1234F1Z5.
            PAN: ABCDE1234F.
            Turnover: 5000000 INR.
            """,
            "MANUAL_REVIEW",
        ),
    ]

    for title, text, expected_status in test_cases:
        test_requirements = (
            ["GST", "PAN", "verify:Original certificates"]
            if expected_status == "MANUAL_REVIEW"
            else requirements
        )

        result = check_compliance(text, test_requirements)

        print(f"\n--- {title} ---")
        print("Expected:", expected_status)
        print("Actual:", result["status"])
        print("Score:", result["score"])
        print("Matched:", result["matched_requirements"])
        print("Missing:", result["missing_requirements"])
        print("Manual review:", result["manual_review"])
