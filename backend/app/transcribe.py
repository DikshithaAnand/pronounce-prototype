import re
from .model_loader import get_model

def clean_word(text: str) -> str:
    """
    Removes punctuation to ensure 'Hello,' matches 'hello' in scoring.
    """
    return re.sub(r'[^\w\s]', '', text).strip()

def transcribe_with_words(audio_path: str, language: str = "en"):
    """
    Dyslexia-optimized transcription.
    
    Features:
    - VAD Filter: Ignores heavy breathing/thinking noises.
    - Confidence Scores: Detects uncertainty/mumbling.
    - Precise Timing: Captures hesitation intervals.
    """
    
    model = get_model()
    
    # 1. Transcribe with VAD to reduce hallucinations during silence
    segments, info = model.transcribe(
        audio_path,
        language=language,
        task="transcribe",
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        beam_size=5
    )
    
    words = []
    full_text_parts = []
    prev_end = 0.0
    
    for segment in segments:
        full_text_parts.append(segment.text)
        
        if not segment.words:
            continue
            
        for w in segment.words:
            start = float(w.start)
            end = float(w.end)
            duration = end - start
            
            # Calculate pause before this word
            pause_before = max(0.0, start - prev_end)
            
            # Clean punctuation for downstream scoring
            cleaned = clean_word(w.word)
            
            if cleaned:
                words.append({
                    "word": cleaned,
                    "original_word": w.word.strip(),
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "duration": round(duration, 3),
                    "pause_before": round(pause_before, 3),
                    "confidence": round(w.probability, 4)  # CRITICAL for dyslexia
                })
            
            prev_end = end

    return {
        "text": " ".join(full_text_parts).strip(),
        "words": words,
        "language_probs": info.language_probability
    }