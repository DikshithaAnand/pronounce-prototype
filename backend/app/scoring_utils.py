import difflib

def calculate_fluency(wpm, accuracy_pct):
    """
    Calculates a 0-100 fluency score based on Speed (WPM) and Accuracy.
    Target WPM for conversational reading is roughly 100-130.
    """
    # 1. Pace Score (Targeting ~110 WPM as ideal)
    # If WPM is 0-110, score scales up. If > 110, it stays high unless rushing (>160).
    if wpm > 160:
        pace_score = max(0, 100 - (wpm - 160)) # Penalty for rushing
    else:
        pace_score = min(100, (wpm / 110) * 100)
    
    # 2. Weighted Score: Accuracy matters more than speed for learners
    # Formula: 60% Accuracy + 40% Pace
    fluency = (accuracy_pct * 0.6) + (pace_score * 0.4)
    
    return round(fluency, 1)

def generate_analysis_report(alignment: list, target_text: str, duration_sec: float):
    
    # --- 1. Basic Counts ---
    total_words = len(target_text.split())
    safe_duration_min = max(duration_sec / 60, 0.001)
    
    # Count Standard Metrics
    correct_count = 0  # <--- NEW: Track Success
    substitutions = 0
    deletions = 0
    stutters = 0
    mispronunciations = 0
    insertions = 0
    
    error_report = []

    for item in alignment:
        status = item.get("status")
        target = item.get("target", "")
        recognized = item.get("recognized", "")

        if status == "correct":
            correct_count += 1  # Increment Success

        elif status == "substitution":
            similarity = difflib.SequenceMatcher(None, target.lower(), recognized.lower()).ratio()
            if similarity > 0.4:
                mispronunciations += 1
                e_type = "mispronunciation"
            else:
                substitutions += 1
                e_type = "substitution"
            
            error_report.append({
                "type": e_type, "expected": target, "actual": recognized,
                "similarity": round(similarity * 100, 1)
            })

        elif status == "deletion":
            deletions += 1
            error_report.append({"type": "deletion", "expected": target, "actual": "(Skipped)"})

        elif status == "stutter":
            stutters += 1
        
        elif status == "insertion":
            insertions += 1

    # --- 2. Advanced Metrics ---
    
    # WPM (Words Per Minute)
    # We use 'correct_count' for WPM to measure "Correct Words Per Minute" (CWPM) 
    # which is a stricter/better measure than just total words.
    wpm = int(correct_count / safe_duration_min)
    
    # Accuracy Percentage
    # Avoid division by zero
    accuracy_pct = 0
    if total_words > 0:
        accuracy_pct = round((correct_count / total_words) * 100, 1)

    # Fluency Score (New Calculation)
    fluency_score = calculate_fluency(wpm, accuracy_pct)

    metrics = {
        "wpm": wpm,
        "accuracy": accuracy_pct,
        "fluency": fluency_score,
        "correct_count": correct_count,  # <--- Sent to frontend
        "stutter_count": stutters,
        "deletion_count": deletions,
        "substitution_count": substitutions,
        "mispronunciation_count": mispronunciations,
        "insertion_count": insertions
    }

    return metrics, error_report