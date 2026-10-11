def check_tender_rules(pdf_text):
    requirements = ["pan", "gst", "experience", "turnover"]
    lower_text = pdf_text.lower()
    
    passed_items = []
    failed_items = []
    
    for item in requirements:
        if item in lower_text:
            passed_items.append(item)
        else:
            failed_items.append(item)
            
    total_count = len(requirements)
    passed_count = len(passed_items)
    percentage = (passed_count / total_count) * 100
    
    if percentage >= 75:
        verdict = "VERIFIED"
    else:
        verdict = "REJECTED"
        
    return {
        "verdict": verdict,
        "score": percentage,
        "passed_items": passed_items,
        "failed_items": failed_items
    }