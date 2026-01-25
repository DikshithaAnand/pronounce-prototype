from pydub import AudioSegment
from pydub.silence import detect_silence
import logging

logger = logging.getLogger(__name__)

def validate_audio(file_path: str):
    """
    Analyzes audio quality with DYSLEXIA-FRIENDLY tolerances.
    """
    try:
        audio = AudioSegment.from_file(file_path)
        
        # 1. DURATION CHECK
        # Keep this small to catch accidental clicks
        duration_sec = audio.duration_seconds
        if duration_sec < 1.0:
            return False, f"Recording too short ({round(duration_sec, 1)}s). Please keep reading."

        # 2. VOLUME CHECK
        # Rejection: Quieter than -50dBFS (Very faint/Whisper)
        max_volume = audio.max_dBFS
        if max_volume < -50.0:
            return False, "Volume too low. Please speak closer to the mic."

        # 3. SILENCE CHECK (The Fix)
        # Old Logic: 500ms pause = Silence.
        # New Logic: 2000ms (2s) pause = Silence. 
        # Anything shorter is considered "Thinking Time" (Active).
        
        silence_thresh = max_volume - 20 # Be more generous with background noise
        silent_ranges = detect_silence(
            audio, 
            min_silence_len=2000, # <--- CHANGED: Pauses under 2s are IGNORED
            silence_thresh=silence_thresh
        )
        
        total_silence_ms = sum([(end - start) for start, end in silent_ranges])
        total_duration_ms = len(audio)
        silence_ratio = total_silence_ms / total_duration_ms

        # Rejection: Only reject if >90% of the file is TOTAL silence (2s+ chunks)
        if silence_ratio > 0.90:
            return False, "No speech detected. Did you forget to speak?"

        return True, None

    except Exception as e:
        logger.error(f"Validation Error: {e}")
        # Fail open (allow processing) if validation crashes
        return True, None