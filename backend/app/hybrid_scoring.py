from .transcribe import transcribe_with_words
from .scoring import compute_text_score
from .audio_scoring import compute_acoustic_clarity

# ---------------------------
# Fluency Logic
# ---------------------------

def compute_fluency_metrics(words):
    """
    Calculates WPM and Dysfluency events (blocks/pauses).
    """
    total_words = len(words)
    if total_words == 0:
        return {"wpm": 0, "avg_pause": 0, "blocks": 0}
        
    start_time = words[0]["start"]
    end_time = words[-1]["end"]
    
    duration_min = max((end_time - start_time) / 60.0, 0.001)
    wpm = total_words / duration_min
    
    # Analyze Pauses
    # Skip first word (initial latency is not a dysfluency)
    pauses = [w["pause_before"] for w in words[1:] if w["pause_before"] is not None]
    
    avg_pause = sum(pauses) / len(pauses) if pauses else 0.0
    
    # "Blocks" are significant struggles > 1.5s
    blocks = len([p for p in pauses if p > 1.5])
    
    return {
        "wpm": round(wpm, 1),
        "avg_pause": round(avg_pause, 2),
        "blocks": blocks
    }

def normalize_wpm_score(wpm):
    """
    Scores WPM based on 'Comfortable Reading' not 'Speed Reading'.
    """
    if wpm >= 110: return 100  # Fluent
    if wpm <= 20: return 20    # Struggling
    return (wpm / 110) * 100

# ---------------------------
# MAIN PIPELINE
# ---------------------------

def compute_per_word_scores(target_text, lang_code, audio_path):
    """
    Full Assessment Pipeline.
    """
    
    # 1. Transcribe (Speech -> Text + Time)
    trans_result = transcribe_with_words(audio_path, language=lang_code)
    words = trans_result["words"]
    rec_text = trans_result["text"]
    
    # 2. Text Scoring (Accuracy + Stutter Detection)
    text_result = compute_text_score(target_text, rec_text)
    
    # 3. Acoustic Scoring (Clarity + Confidence)
    acoustic_result = compute_acoustic_clarity(audio_path, words)
    
    # 4. Fluency Scoring (Speed + Pauses)
    fluency_stats = compute_fluency_metrics(words)
    fluency_score = normalize_wpm_score(fluency_stats["wpm"])
    
    # 5. Final Composite Score
    # Weighting: 50% Accuracy, 30% Fluency, 20% Clarity
    final_score = (
        0.50 * text_result["text_score"] +
        0.30 * fluency_score +
        0.20 * acoustic_result["clarity_score"]
    )
    
    return {
        "overall_score": round(final_score, 1),
        
        "components": {
            "accuracy": text_result["text_score"],
            "fluency": round(fluency_score, 1),
            "clarity": acoustic_result["clarity_score"]
        },
        
        "detailed_metrics": {
            "wpm": fluency_stats["wpm"],
            "blocks": fluency_stats["blocks"],
            "stutters": text_result["metrics"]["stutters"],
            "correct_words": text_result["metrics"]["correct"],
            "total_words_read": len(words)
        },
        
        "recognized_text": rec_text,
        "word_alignment": text_result["word_alignment"]
    }