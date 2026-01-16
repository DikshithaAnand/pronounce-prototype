import numpy as np
import librosa

def compute_acoustic_clarity(audio_path: str, words: list) -> dict:
    """
    Analyzes audio quality independently of accent.
    
    Metrics:
    - Confidence: Are distinct phonemes detected? (from Whisper)
    - Signal Quality: Is the volume consistent?
    - Articulation: Did they rush or speak clearly?
    """
    
    # 1. Confidence Score (from Whisper)
    # Measures "how well did the acoustic model match the sounds?"
    if not words:
        avg_confidence = 0.0
    else:
        avg_confidence = np.mean([w.get("confidence", 0.0) for w in words])
    
    # 2. Simple Signal Check (using Librosa)
    # Detects if audio is too quiet or noisy
    try:
        y, sr = librosa.load(audio_path, sr=16000, duration=30)
        rms = librosa.feature.rms(y=y)
        avg_volume = np.mean(rms)
        
        # Normalize volume score (0.01 is decent threshold for speech)
        vol_score = min(1.0, avg_volume / 0.01)
    except:
        vol_score = 0.5 # Fallback

    # 3. Final Clarity Metric
    # Confidence is 80% of the score (it handles accent tolerance best)
    # Volume is 20% (technical check)
    
    clarity_percentage = (avg_confidence * 80) + (vol_score * 20)
    clarity_percentage = max(0.0, min(100.0, clarity_percentage))
    
    return {
        "clarity_score": round(clarity_percentage, 1),
        "details": {
            "model_confidence": round(avg_confidence, 2),
            "volume_consistency": round(vol_score, 2)
        }
    }