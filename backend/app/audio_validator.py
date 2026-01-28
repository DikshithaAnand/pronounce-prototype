from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import logging

logger = logging.getLogger(__name__)

def validate_audio(file_path: str):
    """
    Analyzes audio for presence of speech.
    Strategy: Fixed Threshold. Anything louder than -40dB is considered 'Activity'.
    """
    try:
        audio = AudioSegment.from_file(file_path)
        
        # 1. DURATION CHECK
        if audio.duration_seconds < 0.5:
            return False, "Recording too short."

        # 2. DEAD MIC CHECK
        # If the loudest sound is quieter than -50dB, the mic is probably dead/muted.
        if audio.max_dBFS < -50.0:
            return False, "Volume too low. Please speak closer to the mic."

        # 3. ACTIVITY CHECK (Fixed Threshold)
        # We don't use 'peak - 16' anymore because accidental clicks break it.
        # We look for ANY audio louder than -40dB (A quiet library level).
        
        nonsilent_ranges = detect_nonsilent(
            audio,
            min_silence_len=500, # A gap must be 0.5s to break a chunk
            silence_thresh=-40   # <--- FIXED THRESHOLD
        )
        
        total_active_ms = sum([(end - start) for start, end in nonsilent_ranges])
        total_active_sec = total_active_ms / 1000.0
        
        logger.info(f"🎤 Active Audio (> -40dB): {total_active_sec}s")

        # As long as there is 0.5s of noise/speech, we let Whisper handle it.
        if total_active_sec < 0.5:
             # Fallback: If RMS (Average Energy) is decent, let it pass anyway.
             if audio.dBFS > -45:
                 logger.info("⚠️ Low activity detected, but average volume is okay. Accepting.")
                 return True, None
             
             return False, "No clear speech detected."

        return True, None

    except Exception as e:
        logger.error(f"Validation Error: {e}")
        return True, None # Fail Open