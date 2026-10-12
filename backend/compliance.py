def check_tender_rules(text):
    rules = ["pan", "gst", "experience", "turnover"]
    lower_text = text.lower()
    count = 0
    
    for word in rules:
        if word in lower_text:
            count = count + 1
            
    score = (count / len(rules)) * 100
    if score >= 75:
        status = "VERIFIED"
    else:
        status = "REJECTED"
        
    return {
        "status": status,
        "score": score
    }