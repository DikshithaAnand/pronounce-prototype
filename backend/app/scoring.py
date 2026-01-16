import unicodedata
import re
from difflib import SequenceMatcher
from jiwer import wer

# -------------------------------
# Normalization
# -------------------------------

def normalize_text(text: str) -> str:
    """
    Standardizes text for comparison (lower, no punct, unicode fix).
    """
    if not text:
        return ""
    
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u200c", "").replace("\u200d", "")
    
    cleaned = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith("P") or cat.startswith("S"):
            continue
        cleaned.append(ch)
    
    text = "".join(cleaned).lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text

def tokenize(text: str):
    return normalize_text(text).split() if text else []

# -------------------------------
# Dyslexia-aware scoring
# -------------------------------

def compute_text_score(target: str, recognized: str) -> dict:
    """
    Aligns text and calculates accuracy with empathy.
    
    Key Dyslexia Logic:
    - Stuttering (The The) -> 10% Penalty (Almost ignored)
    - Insertion (The [blue] dog) -> 40% Penalty
    - Substitution (The [cat] ran) -> 100% Penalty
    """
    
    target_tokens = tokenize(target)
    rec_tokens = tokenize(recognized)
    
    if not target_tokens:
        return {"text_score": 0.0, "word_alignment": []}

    sm = SequenceMatcher(None, target_tokens, rec_tokens)
    alignment = []
    
    # Metrics
    metrics = {
        "correct": 0,
        "substitutions": 0,
        "deletions": 0,
        "insertions": 0,
        "stutters": 0  # Self-corrections
    }
    
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        
        if tag == "equal":
            for ti, ri in zip(range(i1, i2), range(j1, j2)):
                alignment.append({
                    "target": target_tokens[ti],
                    "recognized": rec_tokens[ri],
                    "status": "correct"
                })
                metrics["correct"] += 1
                
        elif tag == "replace":
            for ti, ri in zip(range(i1, i2), range(j1, j2)):
                alignment.append({
                    "target": target_tokens[ti],
                    "recognized": rec_tokens[ri],
                    "status": "substitution"
                })
                metrics["substitutions"] += 1
                
        elif tag == "delete":
            for ti in range(i1, i2):
                alignment.append({
                    "target": target_tokens[ti],
                    "recognized": "",
                    "status": "deletion"
                })
                metrics["deletions"] += 1
                
        elif tag == "insert":
            for ri in range(j1, j2):
                word_inserted = rec_tokens[ri]
                
                # Check for Stutter: Is this word identical to the previous one?
                is_stutter = False
                if ri > 0 and rec_tokens[ri-1] == word_inserted:
                    is_stutter = True
                
                status_label = "stutter" if is_stutter else "insertion"
                
                alignment.append({
                    "target": "",
                    "recognized": word_inserted,
                    "status": status_label
                })
                
                if is_stutter:
                    metrics["stutters"] += 1
                else:
                    metrics["insertions"] += 1

    # -------------------------------
    # Scoring Calculation
    # -------------------------------
    
    total_target = len(target_tokens)
    
    if total_target == 0:
        score = 0.0
    else:
        # Weighted Penalties
        penalty = (
            metrics["substitutions"] * 1.0 +  # Strongest
            metrics["deletions"] * 0.8 +      # Moderate
            metrics["insertions"] * 0.4 +     # Light
            metrics["stutters"] * 0.1         # Very Light (Empathy)
        )
        
        raw = (total_target - penalty) / total_target
        score = max(0.0, min(100.0, raw * 100))

    return {
        "text_score": round(score, 1),
        "word_alignment": alignment,
        "metrics": metrics
    }